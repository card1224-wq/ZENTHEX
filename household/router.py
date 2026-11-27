"""Per-account household records. No bank connection, transfers or trade orders."""
from datetime import date, datetime, time, timedelta, timezone
from datetime import date as DateValue
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from auth.router import get_current_user
from database.models import HouseholdEntry, HouseholdSettings, TradeRecord
from database.session import get_db

router = APIRouter(prefix='/api/household', tags=['household'])
KST = timezone(timedelta(hours=9))


def owner(response: Response, Authorization: str = Header(None), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    if not Authorization or not Authorization.startswith('Bearer '):
        raise HTTPException(401, '가계부는 로그인이 필요합니다.')
    user = get_current_user(Authorization[7:], db)
    if not user.is_active or user.approval_status != 'approved':
        raise HTTPException(403, '계정 상태를 확인해주세요.')
    return user.id


class SettingInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    as_of: date = Field(ge=date(2000, 1, 1), le=date(2100, 12, 31))
    cash_krw: int = Field(strict=True, ge=0, le=10**12)
    reserve_krw: int | None = Field(default=None, strict=True, ge=0, le=10**12)


class EntryInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    date: DateValue = Field(ge=DateValue(2000, 1, 1), le=DateValue(2100, 12, 31))
    activity: Literal['household', 'zenthex_business', 'betman', 'other'] = 'household'
    kind: Literal['income', 'expense', 'card_purchase', 'card_payment', 'transfer']
    category: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=160)
    method: str = Field(default='계좌', min_length=1, max_length=40)
    amount_krw: int | None = Field(default=None, strict=True, ge=0, le=10**12)
    status: Literal['planned', 'done'] = 'planned'
    confirmed: bool = True

    @model_validator(mode='after')
    def validate_record(self):
        if self.status == 'done' and self.amount_krw is None:
            raise ValueError('완료한 거래는 실제 금액을 입력하세요.')
        if not self.description.strip() or not self.category.strip():
            raise ValueError('내용과 분류를 입력하세요.')
        if self.activity != 'household' and self.kind not in {'income', 'expense'}:
            raise ValueError('별도 활동은 수입·지출로 기록하세요.')
        return self


def records(db, user_id):
    return db.query(HouseholdEntry).filter(HouseholdEntry.user_id == user_id, HouseholdEntry.deleted.is_(False))


def serialize(row):
    return {name: getattr(row, name) for name in (
        'id', 'date', 'activity', 'kind', 'category', 'description', 'method', 'amount_krw', 'status', 'confirmed')}


def setting_value(row):
    return {'as_of': row.as_of, 'cash_krw': row.cash_krw, 'reserve_krw': row.reserve_krw} if row else None


def month_bounds(month):
    try:
        start = date.fromisoformat(month + '-01')
        end = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
        if not 2000 <= start.year <= 2100:
            raise ValueError()
        return start, end
    except (ValueError, TypeError):
        raise HTTPException(422, '조회 월은 YYYY-MM 형식으로 입력하세요.')


@router.put('/settings')
def save_settings(data: SettingInput, user_id: int = Depends(owner), db: Session = Depends(get_db)):
    row = db.get(HouseholdSettings, user_id)
    if not row:
        row = HouseholdSettings(user_id=user_id)
        db.add(row)
    for name, value in data.model_dump().items():
        setattr(row, name, value)
    db.commit()
    return setting_value(row)


@router.post('/entries', status_code=201)
def create_entry(data: EntryInput, user_id: int = Depends(owner), db: Session = Depends(get_db)):
    row = HouseholdEntry(user_id=user_id, **data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.put('/entries/{entry_id}')
def edit_entry(entry_id: int, data: EntryInput, user_id: int = Depends(owner), db: Session = Depends(get_db)):
    row = records(db, user_id).filter(HouseholdEntry.id == entry_id).first()
    if not row:
        raise HTTPException(404, '내역을 찾을 수 없습니다.')
    for name, value in data.model_dump().items():
        setattr(row, name, value)
    db.commit()
    return serialize(row)


@router.delete('/entries/{entry_id}')
def delete_entry(entry_id: int, user_id: int = Depends(owner), db: Session = Depends(get_db)):
    row = records(db, user_id).filter(HouseholdEntry.id == entry_id).first()
    if not row:
        raise HTTPException(404, '내역을 찾을 수 없습니다.')
    row.deleted = True
    db.commit()
    return {'deleted': True}


@router.get('/entries')
def list_entries(month: str = Query(pattern=r'^\d{4}-\d{2}$'), offset: int = Query(0, ge=0),
                 user_id: int = Depends(owner), db: Session = Depends(get_db)):
    start, end = month_bounds(month)
    query = records(db, user_id).filter(HouseholdEntry.date >= start, HouseholdEntry.date < end)
    total = query.count()
    rows = query.order_by(HouseholdEntry.date.desc(), HouseholdEntry.id.desc()).offset(offset).limit(100).all()
    return {'entries': [serialize(row) for row in rows], 'total': total,
            'next_offset': offset + len(rows) if offset + len(rows) < total else None}


def forecast(rows, settings):
    if not settings:
        return {'days': [], 'minimum_known_balance_krw': None, 'additional_needed_krw': None,
                'unknown_amounts': 0, 'overdue_expenses': 0}
    first, last = settings.as_of, settings.as_of + timedelta(days=35)
    planned = [row for row in rows if row.activity == 'household' and row.status == 'planned'
               and row.confirmed and row.kind in {'income', 'expense', 'card_payment'} and row.date <= last]
    cash, minimum = settings.cash_krw, settings.cash_krw
    unknown, overdue, days = 0, 0, []
    for offset in range(36):
        day = first + timedelta(days=offset)
        incoming = outgoing = 0
        for row in planned:
            effective = max(row.date, first) if row.kind != 'income' else row.date
            if effective != day:
                continue
            if row.date < first:
                overdue += 1
            if row.amount_krw is None:
                unknown += 1
                cash = None
            elif row.kind == 'income':
                incoming += row.amount_krw
            else:
                outgoing += row.amount_krw
        if cash is not None:
            cash += incoming - outgoing
            minimum = min(minimum, cash)
        days.append({'date': day, 'income_krw': incoming, 'outflow_krw': outgoing, 'balance_krw': cash})
    return {'days': days, 'minimum_known_balance_krw': minimum,
            'additional_needed_krw': max(0, (settings.reserve_krw or 0) - minimum),
            'reserve_entered': settings.reserve_krw is not None, 'unknown_amounts': unknown,
            'overdue_expenses': overdue}


@router.get('/summary')
def summary(month: str | None = Query(None, pattern=r'^\d{4}-\d{2}$'),
            user_id: int = Depends(owner), db: Session = Depends(get_db)):
    month = month or datetime.now(KST).strftime('%Y-%m')
    start, end = month_bounds(month)
    settings = db.get(HouseholdSettings, user_id)
    period = (HouseholdEntry.date >= start) & (HouseholdEntry.date < end)
    if settings:
        period = or_(period, (HouseholdEntry.status == 'planned') & (HouseholdEntry.date <= settings.as_of + timedelta(days=35)))
    rows = records(db, user_id).filter(period).all()
    done = [r for r in rows if start <= r.date < end and r.status == 'done']
    own = [r for r in done if r.activity == 'household']
    income = sum(r.amount_krw for r in own if r.kind == 'income')
    outflow = sum(r.amount_krw for r in own if r.kind in {'expense', 'card_payment'})
    cards = sum(r.amount_krw for r in own if r.kind == 'card_purchase')
    categories = {}
    for row in own:
        if row.kind in {'expense', 'card_payment'}:
            categories[row.category] = categories.get(row.category, 0) + row.amount_krw
    side = {}
    for activity in ('zenthex_business', 'betman', 'other'):
        group = [r for r in done if r.activity == activity]
        side[activity] = {'count': len(group), 'net_krw': sum(r.amount_krw * (1 if r.kind == 'income' else -1) for r in group)}
    utc_start = datetime.combine(start, time.min, KST).astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = datetime.combine(end, time.min, KST).astimezone(timezone.utc).replace(tzinfo=None)
    trade_count, trade_pnl = db.query(func.count(TradeRecord.id), func.sum(TradeRecord.pnl_krw)).filter(
        TradeRecord.user_id == user_id, TradeRecord.mode.in_(['real', 'bithumb_real']),
        TradeRecord.created_at >= utc_start, TradeRecord.created_at < utc_end).one()
    return {'month': month, 'settings': setting_value(settings),
            'actual': {'count': len(own), 'income_krw': income, 'outflow_krw': outflow, 'net_krw': income - outflow,
                       'card_purchases_krw': cards, 'categories': categories},
            'side_activities': side, 'trading': {'count': trade_count, 'realized_pnl_krw': round(trade_pnl or 0, 2)},
            'forecast': forecast(rows, settings)}


@router.get('/export')
def export_data(response: Response, user_id: int = Depends(owner), db: Session = Depends(get_db)):
    response.headers['Content-Disposition'] = 'attachment; filename="zenthex-household.json"'
    return {'schemaVersion': 1, 'settings': setting_value(db.get(HouseholdSettings, user_id)),
            'entries': [serialize(row) for row in records(db, user_id).order_by(HouseholdEntry.date, HouseholdEntry.id).all()],
            'scope': '본인이 입력한 가계부. 은행 자동 연동이나 자동 이체는 포함하지 않습니다.'}
