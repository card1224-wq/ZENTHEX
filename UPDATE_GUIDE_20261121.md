# 2026-11-21 업데이트 적용

## 1. GitHub 업로드

압축을 푼 뒤 **그 안의 파일과 폴더를 함께** 저장소 최상위에 업로드한다. ZIP 파일 자체를 코드 대신 업로드하지 않는다.
`static/finance.html`, `studio/router.py`, `trading/router.py`, `deploy/auto_update.py` 등의 **폴더 경로를 보존**해야 한다. 이전처럼 모든 파일을 루트에 넣으면 실행되지 않는다.
운영 DB·키·환경변수·회원 데이터는 이 묶음에 없다. 기존 나머지 파일을 삭제하지 않는다.

이번 묶음은 잘못된 루트 별칭 대신 실제 실행 경로를 복구한다. 다음부터 웹페이지 수정은 `static` 폴더, 각 API 수정은 해당 제품 폴더에 한다.

Render 게이트웨이는 이미 AWS로 연결되어 있으므로 일반 기능 수정에는 Render 재배포가 필요 없다. 게이트웨이 자체를 수정할 때만 Render 수동 배포한다.

## 2. AWS에서 자동 반영 1회 설치

GitHub 업로드가 끝난 뒤 **AWS Lightsail SSH**에서 한 줄씩 실행한다.

```bash
cd ~/zenthex
git pull --ff-only
sudo python3 deploy/install_auto_update.py
sudo systemctl start zenthex-auto-update.service
sudo journalctl -u zenthex-auto-update -n 60 --no-pager
```

첫 배포에는 새 가상환경과 패키지 설치가 포함되어 수 분이 걸릴 수 있다. 실패하면 기존 앱은 유지하거나 이전 코드로 복구한다. 결과에 ‘배포 완료’와 커밋 ID가 나오는지 확인한다.

자동 업데이트는 약 2분 간격으로 GitHub main을 확인한다. 빌드/시험은 운영 환경변수와 분리된 `zenthex-build` 계정에서 수행한다. 운영 앱은 기존 `zenthex` 계정으로 실행한다. 새 SSH 접속 포트·비밀번호·GitHub 쓰기 키는 필요 없다. 현재 공개 저장소 전용이며 비공개 전환 시 별도 읽기 인증 설정이 필요하다.

**중요:** `ZENTHEX_ENABLE_LIVE_TRADING=true`, 엔진 실행/보유·미확정 주문, Studio 생성 중에는 코드 교체를 보류한다. 일시정지만으로 실거래 권한 설정까지 꺼지는 것은 아니다. 거래 중에는 강제로 업데이트하지 않는다.

실패한 동일 커밋은 반복 설치하지 않는다. 설정 문제를 해결한 후 재시험하려면:

```bash
sudo python3 /usr/local/lib/zenthex/auto_update.py --retry
```

자동 업데이트를 중지하려면:

```bash
sudo systemctl disable --now zenthex-auto-update.timer
```

코드 복구와 DB 복구는 다르다. 자동 실패 복구는 이전 코드를 재시작하며 DB를 과거 시점으로 덮어쓰지 않는다. DB 백업은 `/var/backups/zenthex-security/deploy-*`에 보관한다. 대규모/비호환 DB 마이그레이션은 별도 배포 작업으로 다룬다.

## 3. 연결 확인

```bash
python3 zenthex_connection_check.py --public --verify-outbound
```

홈페이지에서 새로고침 후 로그인·기존 데이터·제품별 상태를 확인한다. 페이지 200은 실제 외부 생성/체결 성공을 뜻하지 않는다.

## 4. Studio 실제 API 설정

AI 키가 AWS에 없다면 (Render 환경변수에 있는 것만으로 AWS에 전달되지 않는다):

```bash
sudo python3 zenthex_configure_studio.py
```

Google AI Studio 키를 터미널의 숨김 입력에 넣는다. 채팅·GitHub에 키를 올리지 않는다. 기존 비밀번호는 바꾸지 않는다. 실제 이미지 생성 요청으로 API 권한·결제 한도를 확인한다.

현재 실제 생성 결과는 AI 건축 콘셉트 이미지다. 정확한 치수 기반 GLB·OBJ 완성 기능이라고 판매하지 않는다.

## 5. 업비트 개인 실거래 시작 권한

자동 배포와 Studio 설정을 먼저 끝낸다. 다음 명령은 대표 계정·정지 상태·HTTPS·실제 발신 IP를 점검한다.

```bash
sudo python3 zenthex_enable_live.py 13.124.81.242
```

점검 통과 후 실거래 시작 권한만 켜려면:

```bash
sudo python3 zenthex_enable_live.py 13.124.81.242 --enable
```

비밀번호·계정·API 키·DB는 변경하지 않는다. 주문도 보내지 않는다. 기존 `zenthex_live_test.py --arm`은 비밀번호를 재설정하므로 이번 흐름에서는 사용하지 않는다.

그다음 웹에서 업비트 실거래 모드를 직접 선택하고, API 키 인증·고정 IP·투자금·손절·익절·반복 여부를 확인한다. 실제 주문은 사용자가 명시적으로 시작할 때만 발생한다. 첫 확인은 반복 재탐색을 끈 상태에서 체결 UUID와 거래소 내역을 대조한다. 통신 오류가 나면 시작을 반복 클릭하지 않고 실제 주문·보유 상태를 먼저 확인한다.

모의매매는 선택 기능이며 완료 실적을 실거래 허용의 필수 조건으로 추가하지 않았다. 모의매매 시작 시 실거래로 자동 전환되는 버그는 수정했다.

## 검증 범위

- 오프라인 기능/주문/복구/배포 시험 49개 통과.
- 주요 API·HTML·상태 스크립트 응답 9개 확인.
- JavaScript 문법 검사 5개 통과.
- 실제 거래소 주문, 실제 Gemini 생성, AWS 신규 배포는 로컬 시험에 포함되지 않는다.
- `PRODUCT_REQUIREMENTS_20261121.md`에 구현/미구현과 제품 완성 기준을 기록했다.
