# Zenthex 서울 고정 IP 서버(VPS) 이전 가이드

## 왜 옮기나

| 문제 | Render 무료 (기존) | 서울 VPS (이전 후) |
|---|---|---|
| 거래소 허용 IP | 서버 IP가 계속 바뀌어 등록 불가 | 고정 IP 1개 → 등록하면 끝 |
| 24시간 자동매매 | 15분 접속 없으면 서버가 잠들어 봇 정지 | 항상 켜져 있음 |
| 회원/구독 DB | 재배포마다 초기화 | `/var/lib/zenthex/`에 영구 보관 |

설계도 원칙 "엔진은 사용자 PC가 아니라 Zenthex 서버에서 24시간 실행"을 지키기 위한 이전입니다.
코드 구조(Studio / Trading / Stock, 구독 권한, 리스크 매니저)는 바뀌지 않습니다.

---

## 1단계. Lightsail 서버 만들기 (약 5분)

1. https://lightsail.aws.amazon.com 접속 → AWS 계정으로 로그인 (없으면 가입, 카드 등록 필요)
2. **인스턴스 생성**
   - 리전: **서울 (ap-northeast-2)**
   - 플랫폼: **Linux/Unix**
   - 블루프린트: **운영 체제(OS) 전용 → Ubuntu 24.04 LTS**
   - 플랜: **메모리 1GB 이상** (512MB는 패키지 설치 중 멈출 수 있음)
   - 이름: `zenthex`
3. 생성 후 1~2분 기다리면 상태가 "실행 중"이 됩니다.

## 2단계. 고정 IP 붙이기 (꼭 3단계보다 먼저!)

1. Lightsail 왼쪽 메뉴 **네트워킹** → **고정 IP 생성**
2. 리전 서울, 연결할 인스턴스 `zenthex` 선택 → 생성
3. 화면에 나온 IP(예: `3.xx.xx.xx`)를 메모합니다. **이것이 젠텍스 서버 IP입니다.**
   - 인스턴스에 연결된 동안 고정 IP는 무료입니다. 연결 안 된 고정 IP만 요금이 붙습니다.
4. 인스턴스 → **네트워킹** 탭 → IPv4 방화벽에 `HTTP 80`이 열려 있는지 확인 (기본 열림). 나중에 도메인을 붙이면 `HTTPS 443`도 추가합니다.

## 3단계. 젠텍스 코드 올리고 설치 (약 10분)

1. 인스턴스 화면에서 **SSH를 사용하여 연결** (브라우저에 검은 터미널 창이 뜸)
2. 터미널 창 오른쪽 위 메뉴에서 **파일 업로드** → `zenthex-saas-upload-...zip` 파일 선택
3. 아래 명령어를 한 줄씩 붙여넣고 엔터:

```bash
sudo apt-get update && sudo apt-get install -y unzip
mkdir -p ~/zenthex && cd ~/zenthex
unzip -o ~/zenthex-saas-upload-*.zip
sudo bash deploy/setup_vps.sh
```

4. 마지막에 아래처럼 나오면 성공입니다:

```
 Zenthex 설치 완료
 홈페이지 주소 : http://3.xx.xx.xx
 거래소 허용 IP: 3.xx.xx.xx
```

   → 이 IP가 2단계에서 메모한 고정 IP와 **같은지** 확인하세요.

5. Studio용 Gemini 키 넣기:

```bash
sudo nano /etc/zenthex/zenthex.env
```
   `GEMINI_API_KEY=` 뒤에 키를 붙여넣고 `Ctrl+O` → 엔터 → `Ctrl+X`로 저장 후:
```bash
sudo systemctl restart zenthex
```

## 4단계. IP 확인 → 거래소 등록 → 소액 테스트

1. 브라우저에서 `http://고정IP/finance.html` 접속 → 로그인
2. API 키 설정 열기 → **Zenthex 고정 IP 확인** 버튼
   - 초록색 "정상: … 일치합니다" → 다음 단계 진행
   - 빨간색이면 진행하지 말고 메시지를 캡처해서 보여주세요.
3. 업비트(또는 빗썸) → Open API 관리 → **새 키 발급**
   - 권한: 자산조회 + 주문하기만 ✅ / **출금 ❌**
   - 허용 IP: 위 고정 IP 1개
4. 젠텍스에서 키 진단 → 키 인증 → 잔고 불러오기
5. **5,000~10,000원**으로 실거래 1회: 매수 → 목표/손절 매도 → 엔진 종료까지 확인

---

## 코드 업데이트 방법 (앞으로 수정본 받을 때)

새 zip을 같은 방식으로 업로드한 뒤:

```bash
rm -rf ~/zenthex-new && mkdir ~/zenthex-new && cd ~/zenthex-new
unzip -o ~/새파일이름.zip
sudo bash deploy/update_vps.sh
```

- DB는 업데이트 전에 자동 백업되고, 회원/구독/환경변수는 그대로 유지됩니다.
- **봇이 코인을 보유 중일 때는 먼저 '매도 후 정지'를 누르고** 업데이트하세요. (재시작 시 엔진이 멈춥니다)

## 자주 쓰는 명령어

| 하고 싶은 것 | 명령어 |
|---|---|
| 서버 상태 보기 | `sudo systemctl status zenthex` |
| 최근 로그 보기 | `sudo journalctl -u zenthex -n 100 --no-pager` |
| 재시작 | `sudo systemctl restart zenthex` |
| 환경변수 수정 | `sudo nano /etc/zenthex/zenthex.env` → 재시작 |

## 회원 받기 전에 꼭 할 것: 도메인 + HTTPS

지금은 `http://IP` 주소라서 로그인 비밀번호가 암호화되지 않고 전송됩니다. 혼자 테스트할 때는 괜찮지만, **회원을 받기 전에는 도메인을 연결하고 HTTPS를 켜야 합니다.**
도메인(예: `zenthex.co.kr`)을 사서 DNS A 레코드를 고정 IP로 지정한 뒤:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 도메인주소
```

(Lightsail 방화벽에 HTTPS 443 추가 필요)

## Render는?

VPS에서 실거래까지 확인된 뒤 Render 서비스는 **일시 중지(Suspend)** 하면 됩니다. 두 곳에서 봇이 동시에 돌지 않게 하기 위함입니다. `render.yaml`은 삭제하지 않고 남겨둡니다.
