# Dormitory Management System

### 기숙사 통합 관리 시스템

Python Flask와 SQLite를 기반으로 개발한 웹 기반 기숙사 통합 관리 시스템입니다.

학생과 관리자의 기숙사 관련 업무를 효율적으로 처리하기 위해 개발하였으며 상벌점 관리와 이의제기 및 시설 수리 요청과 자동 방 배정 등의 기능을 제공합니다.

또한 YOLO 기반 객체 탐지 인공지능을 활용하여 CCTV 영상에서 사람을 감지하고 해당 구간을 자동으로 기록하는 기능을 구현하였습니다.

## 1. 프로젝트 개요

기숙사에서 발생하는 다양한 관리 업무를 하나의 웹사이트에서 처리하는 것을 목표로 개발하였습니다.

기존의 수작업 중심 관리 방식에서 벗어나 학생이 직접 필요한 서비스를 신청하고 관리자가 웹사이트를 통해 이를 확인하고 처리할 수 있도록 구성하였습니다.

### 주요 개발 목표

- 학생 및 관리자 계정 통합 관리
- 상벌점 기록 및 이의제기 처리 자동화
- 기숙사 시설 수리 요청 관리
- 학년과 성별을 고려한 기숙사 방 배정
- YOLO 기반 CCTV 사람 감지 및 영상 기록
- 웹 기반 관리자 시스템 구축

## 2. 주요 기능

### 2.1 사용자 인증 및 계정 관리

- 학생 회원가입 및 로그인
- 4자리 학번을 이용한 학생 계정 관리
- 관리자와 학생의 접근 권한 구분
- 비밀번호 해시 처리
- Flask Session 기반 로그인 유지
- CSRF 토큰을 이용한 요청 검증
- 관리자에 의한 학생 계정 조회 및 삭제

### 2.2 상벌점 관리

관리자가 학생에게 상점 또는 벌점을 부여하고 학생은 자신의 상벌점 기록을 확인할 수 있습니다.

**관리자 기능**
- 학생 학번을 통한 상벌점 부여
- 학생별 상점 및 벌점 조회
- 누적 상벌점 합계 계산
- 최근 30일 상점 획득 1위 조회
- 상벌점 부여 내역 관리

**학생 기능**
- 자신의 상벌점 기록 조회
- 상벌점 부여 사유 확인
- 상벌점 이의제기 신청
- 이의제기 처리 결과 확인

### 2.3 상벌점 이의제기

학생이 부여받은 상벌점에 대해 이의제기를 신청하면 관리자가 내용을 확인한 후 승인하거나 반려할 수 있습니다.

이의제기 상태는 다음과 같이 관리됩니다.

| 상태 | 설명 |
|---|---|
| `pending` | 심사 대기 |
| `approved` | 승인 |
| `rejected` | 반려 |

### 2.4 시설 수리 요청

학생이 기숙사 시설의 고장 내용을 등록하면 관리자가 요청을 확인하고 처리할 수 있습니다.

- 호실 및 학생 정보 입력
- 시설 고장 내용 등록
- 학생별 수리 요청 기록 관리
- 관리자 수리 요청 목록 조회
- 수리 완료 여부 처리
- 수리 요청 및 완료 시간 기록

### 2.5 기숙사 자동 방 배정

Python 기반 방 배정 알고리즘을 통해 학생들의 호실을 자동으로 배정합니다.

**주요 기능**
- 학년 및 성별에 따른 학생 분류
- 학생 데이터베이스 기반 방 배정
- 방 배정 결과 미리보기
- 배정 결과 저장
- 기숙사 방 추가 및 삭제
- 방 번호 변경
- 학생 간 호실 교환
- 특정 학생 간 동일 호실 배정 제외 설정
- 기존 방 배정 결과 초기화

방 배정과 관련된 알고리즘은 `function/randomroom.py`에서 관리합니다.

### 2.6 AI 기반 CCTV 관리

YOLOv8 객체 탐지 모델을 활용하여 카메라 영상에서 사람을 감지합니다.

사람이 감지되면 영상 기록을 시작하고 사람이 화면에서 사라지면 기록을 종료합니다.

**주요 기능**
- YOLOv8 기반 사람 탐지
- 노트북 내장 카메라 지원
- 사람 감지 시 자동 기록 시작
- 2초 간격 이미지 수집
- 감지 종료 시 MP4 영상 생성
- FFmpeg를 통한 H.264 영상 변환
- 감지 시작 및 종료 시간 기록
- 관리자 전용 영상 조회 및 다운로드
- 외부 Flask 서버로 영상 업로드
- 영상 종료 후 72시간 보관 및 만료 처리 기능

CCTV AI는 `function/cctvai.py`에서 실행되며 Flask 서버와 분리하여 동작할 수 있도록 구성하였습니다.


## 3. 사용 기술

| 구분 | 기술 |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| AI | YOLOv8, Ultralytics |
| Computer Vision | OpenCV |
| Video Processing | FFmpeg |
| HTTP Communication | Requests |
| Authentication | Flask Session, Werkzeug |
| Version Control | Git, GitHub |
| Deployment | Render, Gunicorn |

## 4. 프로젝트 구조

```text
dormitory/
│
├── function/
│   ├── app.py             # Flask 서버 및 REST API
│   ├── randomroom.py      # 자동 방 배정 알고리즘
│   └── cctvai.py          # YOLO 기반 CCTV AI
│
├── templates/
│   ├── login.html         # 로그인 및 회원가입
│   ├── students.html      # 학생 페이지
│   ├── admin.html         # 관리자 페이지
│   │
│   └── static/
│       ├── script.js
│       ├── students.js
│       ├── admin.js
│       ├── gacha.js
│       └── style.css
│
├── captures/              # CCTV 녹화 영상 (로컬 생성)
├── database.db            # SQLite 데이터베이스 (로컬 생성)
├── .flask_secret          # Flask 비밀키 (로컬 생성)
├── requirements.txt       # 서버 의존성 목록
├── .gitignore
└── README.md
```


## 5. 설치 및 실행

### 5.1 프로젝트 다운로드

```bash
git clone https://github.com/seowonjun0710/dormitory.git
cd dormitory
```

### 5.2 Python 라이브러리 설치

웹사이트 실행에 필요한 라이브러리를 설치합니다.

```bash
python -m pip install -r requirements.txt
```

CCTV AI를 별도로 실행하려면 추가 라이브러리를 설치합니다.

```bash
python -m pip install ultralytics opencv-python requests
```

H.264 영상 변환을 위해 FFmpeg도 설치해야 하며 `ffmpeg` 명령어를 실행할 수 있도록 설정해야 합니다.

### 5.3 Flask 서버 실행

프로젝트 최상위 폴더에서 다음 명령어를 실행합니다.

```bash
python -m function.app
```

로컬 웹사이트 주소:

```text
http://127.0.0.1:5000
```

### 5.4 관리자 계정 생성

로컬 환경에서는 다음 명령어를 실행합니다.

```bash
python -m function.app create-admin
```

프로그램의 안내에 따라 관리자 계정 정보를 입력합니다.

Render 배포 환경에서는 별도로 설정된 관리자 계정 생성 기능을 사용합니다.

### 5.5 CCTV AI 실행

```bash
python function/cctvai.py
```

기본적으로 노트북의 카메라를 사용하며 사람을 감지하면 영상 기록을 시작합니다.

`ESC` 키를 누르면 카메라 프로그램이 종료됩니다.

## 6. CCTV 서버 연결

CCTV AI는 로컬 컴퓨터에서 실행되며 감지된 영상을 Flask 서버로 전송할 수 있습니다.

필요한 환경변수는 다음과 같습니다.

| 환경변수 | 역할 |
|---|---|
| `CCTV_SERVER_URL` | Flask 서버 주소 |
| `CCTV_UPLOAD_KEY` | CCTV 업로드 인증키 |
| `SECRET_KEY` | Flask 세션 서명에 사용할 비밀키 |
| `ADMIN_USERNAME` | 배포용 초기 관리자 아이디 |
| `ADMIN_PASSWORD` | 배포용 초기 관리자 비밀번호 |

서버와 CCTV 장치의 `CCTV_UPLOAD_KEY`는 동일해야 합니다.


## 7. 주요 API

### 사용자 관리

| Method | Endpoint | 기능 |
|---|---|---|
| GET/POST | `/register` | 학생 회원가입 |
| GET/POST | `/login` | 로그인 |
| POST | `/logout` | 로그아웃 |

### 상벌점 및 이의제기

| Method | Endpoint | 기능 |
|---|---|---|
| GET | `/api/points` | 학생 상벌점 조회 |
| GET | `/api/admin/points` | 관리자 상벌점 조회 |
| POST | `/api/admin/points` | 상벌점 등록 |
| GET | `/api/admin/points/ranking` | 최근 30일 상점 순위 |
| GET | `/api/admin/points/student` | 학생별 상벌점 조회 |
| GET/POST | `/api/appeals` | 이의제기 조회 및 등록 |
| GET | `/api/admin/appeals` | 관리자 이의제기 조회 |
| POST | `/api/admin/appeals/{id}/review` | 이의제기 심사 |

### 시설 수리

| Method | Endpoint | 기능 |
|---|---|---|
| GET/POST | `/api/repairs` | 학생 수리 요청 |
| GET | `/api/admin/repairs` | 관리자 수리 요청 조회 |
| POST | `/api/admin/repairs/{id}/complete` | 수리 완료 처리 |

### 방 배정

| Method | Endpoint | 기능 |
|---|---|---|
| POST | `/api/admin/rooms/prepare` | 배정 결과 생성 |
| POST | `/api/admin/rooms/save` | 배정 결과 저장 |
| GET | `/api/admin/rooms` | 호실 목록 조회 |
| POST | `/api/admin/rooms/swap` | 학생 호실 교환 |
| POST | `/api/admin/rooms/reset` | 방 배정 초기화 |
| GET/POST | `/api/admin/rooms/exclusions` | 동일 호실 배정 제외 조건 관리 |

### CCTV

| Method | Endpoint | 기능 |
|---|---|---|
| POST | `/api/cctv/upload` | CCTV 영상 업로드 |
| GET | `/api/admin/cctv` | 녹화 영상 목록 조회 |
| GET | `/api/admin/cctv/{id}/video` | 영상 재생 |
| GET | `/api/admin/cctv/{id}/download` | 영상 다운로드 |

관리자 API는 관리자 인증이 필요하며 CCTV 업로드 API는 별도의 인증키를 사용합니다.

## 8. 웹사이트 배포

본 프로젝트는 GitHub와 Render를 이용하여 Flask 웹사이트를 배포하였습니다.

**Render 설정 예시**

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn --bind 0.0.0.0:$PORT function.app:app
```

웹사이트 주소:

https://dormitory-d5sj.onrender.com

### Render 무료 플랜의 제한

- 일정 시간 접속이 없으면 서버가 일시 중지됩니다.
- 재시작이나 재배포 시 로컬 데이터가 사라질 수 있습니다.
- SQLite와 CCTV 영상의 영구 보관을 보장하지 않습니다.
- 실제 운영 시 영구 데이터베이스와 별도 영상 저장소가 필요합니다.

현재 무료 배포 환경은 개발 및 기능 테스트를 목적으로 사용합니다.

## 9. 보안 및 개인정보 보호

본 프로젝트는 학생 정보와 CCTV 영상을 다루므로 개인정보 보호를 중요하게 고려합니다.

- 비밀번호 해시 처리
- 학생 및 관리자 접근 권한 분리
- CSRF 요청 검증
- CCTV 영상 관리자 전용 접근
- CCTV 업로드 인증키 적용
- 비밀키 및 데이터베이스 Git 추적 제외
- CCTV 영상 보관 기간 제한


## 10. 향후 개선 방향

- SQLite에서 영구 데이터베이스로 이전
- CCTV 영상 외부 저장소 구축
- CCTV 영상 자동 삭제 작업의 안정성 개선
- 독립적인 CCTV AI 장치 구축
- 서버 및 CCTV 프로그램 자동 실행
- 장비 오류 발생 시 자동 복구 기능
- 관리자 기능 및 데이터 관리 안정성 개선

본 프로젝트는 기숙사 관리 업무의 효율성을 높이기 위해 개발한 웹 기반 관리 시스템이며 Python 기반 백엔드와 자동화 알고리즘 및 컴퓨터 비전 기술을 통합한 프로젝트입니다.
