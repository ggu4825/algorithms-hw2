# 과제2 · 에이전트와 함께 만드는 URL 단축기

2026-2 **고급알고리즘**(SIT2001-01) 과제2의 **시작 저장소**입니다.
채팅창에 묻고 복사·붙여넣기 하던 방식에서 벗어나, Codespace 안의 에이전트가
저장소를 읽고, 파일을 고치고, 테스트를 직접 돌리게 하는 방법을 익힙니다.

- 과제 안내: [lec-algorithm.github.io/lecture/article/hw2-2026](https://lec-algorithm.github.io/lecture/article/hw2-2026/)
- 수업 슬라이드: [lec-algorithm.github.io/lecture/slides/hw2-2026](https://lec-algorithm.github.io/lecture/slides/hw2-2026/)
- 해시 테이블 복습: [주제 08 해시 테이블](https://lec-algorithm.github.io/lecture/course/topic-08-hashing/)

## 시작하기

1. 이 저장소 상단의 **Use this template** → **Create a new repository**
2. 저장소 이름은 `algorithms-hw2`처럼 정합니다. 공개(Public)로 만듭니다.
3. 만들어진 **내 저장소**에서 **Code** → **Codespaces** 탭 → **Create codespace on main**
4. 왼쪽 막대의 Copilot 아이콘을 눌러 채팅 창을 열고, 창 아래쪽에서 **Agent** 모드를 고릅니다.

## 들어 있는 것

| 파일 | 하는 일 |
| --- | --- |
| `SPEC.md` | 명세 틀. 에이전트가 초안을 쓰고 **본인이 고칩니다** |
| `src/` · `tests/` · `experiments/` | 비어 있습니다. 수업에서 채웁니다 |
| `tools/catchup.sh` | 수업 중 놓친 단계를 따라잡는 스크립트 |
| `Makefile` | `make test` · `make serve` · `make experiment` · `make experiment-linear` |

정답 코드는 들어 있지 않습니다. 에이전트는 작업 공간의 파일을 읽으므로, 정답이
옆에 있으면 그대로 베껴 와서 연습이 되지 않습니다.

## 명령

컨테이너 안(Codespaces 터미널)에서 실행합니다.

| 하고 싶은 것 | 명령 |
| --- | --- |
| 테스트 | `make test` |
| 웹 서버 (포트 8000) | `make serve` |
| 충돌 실험 | `make experiment` |
| 체이닝·선형 탐지 비교 | `make experiment-linear` |
| 놓친 단계 따라잡기 | `sh tools/catchup.sh <단계 번호>` |

외부 라이브러리는 쓰지 않습니다. Python 표준 모듈만으로 충분합니다.
`make experiment`은 고정 용량 해시 테이블의 탐색 비용을 측정해
`experiments/results.csv`와 `experiments/results.svg`에 저장합니다.
실험은 4,093칸을 유지하며 적재율 0.25부터 4.00까지 0.25 간격으로 측정합니다.
성공 탐색은 저장된 모든 URL을 확인하고, 실패 탐색은 무작위 부재 URL 10,000개를
사용합니다. 이론식은 균등한 해시 분포를 가정하므로, 측정값과의 작은 차이는
유한한 URL 표본에서 버킷 분포가 완전히 균등하지 않은 데서 생길 수 있습니다.
`make serve`는 모든 인터페이스에서 기본 포트 8000을 엽니다. 리버스 프록시 뒤에서
쓸 때는 프록시가 `X-Forwarded-Host`와 `X-Forwarded-Proto`를 올바른 공개 origin으로
설정해야 짧은 링크가 브라우저에서 바로 열립니다.
`/table`에서 충돌 처리 방식을 바꿀 수 있으며, 바꿔도 저장한 URL과 코드가 유지됩니다.
`make experiment-linear`는 동일한 URL 표본과 4,093칸으로 개별 체이닝과 선형 탐지를
적재율 0.1부터 0.9까지 비교해
`experiments/linear_probing_results.csv`와
`experiments/linear_probing_results.svg`를 생성합니다.

## 로컬에서 하기

```sh
git clone https://github.com/<본인 계정>/<내 저장소>.git
cd <내 저장소>
docker compose up -d
docker compose exec lab bash
```

**이후 모든 `docker compose` 명령은 이 폴더에서 칩니다.**
