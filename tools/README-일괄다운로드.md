# 인천 교육과정편성표 일괄 다운로드

`fetch_ice_curriculum.py` 는 인천 교육과정편성표 작성시스템(ice-curriculum.kr)의 공개 목록에서
"2026학년도 재학생의 3개년 교육과정 편성표" 엑셀을 학교별로 내려받아 `schools/` 에 저장하고 `schools.json` 을 갱신합니다.

## 준비 (한 번)
1. 파이썬 3 설치 (python.org)
2. 명령 프롬프트에서:  `pip install requests beautifulsoup4`

## 실행 (저장소 폴더에서)
```
python tools/fetch_ice_curriculum.py --limit 2        # 먼저 2개만 받아서 잘 되는지 확인
python tools/fetch_ice_curriculum.py                  # 전체 (약 120개, 3~4분)
```
- `--only 효성,신송` : 학교명에 포함된 것만
- `--year 2025`     : 다른 학년도
- `--delay 2`       : 요청 간격(초). 기본 1.5초. 줄이지 마세요.

## 구·군 분류
이 사이트에는 학교의 구·군 정보가 없어서, `tools/districts.csv` 에 `학교명,구·군` 으로 적어 두면 반영됩니다.
적지 않은 학교는 `schools.json`의 "미분류"에 들어가며, 나중에 CSV를 채우고 스크립트를 다시 실행하면 옮겨집니다.

## 결과 확인
- `tools/ice_download_log.csv` : 학교별 결과(ok/실패)
- 실패에 "엑셀이 아닌 응답(로그인 필요?)"가 뜨면 다운로드에 로그인이 필요한 상태입니다. 그 경우 알려 주세요.

## 올리기
`schools/` 폴더와 `schools.json` 을 깃허브에 올리면 사이트의 학교 선택 목록에 바로 나타납니다.
학교 id(영문)는 학교명을 로마자로 바꿔 자동으로 만들며(예: 인천효성고등학교 → hyoseong), 기존 4개 학교의 id는 그대로 유지됩니다.
