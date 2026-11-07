import asyncio
import time
import urllib.parse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from research.backtest import run_research
from trading.binance_client import _request_json

router = APIRouter(prefix='/api/research', tags=['research'])

class Bar(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    time: int = Field(gt=0)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)

class ReplayRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    market: Literal['upbit', 'binance_futures', 'stock']
    feeBps: float = Field(ge=0, le=1000)
    slippageBps: float = Field(ge=0, le=1000)
    bars: list[Bar] = Field(min_length=200, max_length=20000)

@router.post('/replay')
async def research_replay(config: ReplayRequest):
    try:
        return await asyncio.to_thread(run_research, [b.model_dump() for b in config.bars], config.market, config.feeBps/10000, config.slippageBps/10000)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

# Only public market data; no credentials or order endpoints.
@router.get('/binance-bars')
async def binance_bars():
    try:
        rows = await asyncio.to_thread(_request_json, 'https://fapi.binance.com/fapi/v1/klines?' + urllib.parse.urlencode({'symbol':'BTCUSDT', 'interval':'1h', 'limit':1000}))
        now = int(time.time()*1000)
        return {'source':'Binance USD-M BTCUSDT 1h', 'bars':[dict(time=int(r[0]), open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4])) for r in rows if int(r[6]) < now]}
    except Exception:
        raise HTTPException(502, '공개 시세를 가져오지 못했습니다. CSV를 사용하세요.')
