# spec.json 형식

```json
{
  "base_dir": "/mnt/user-data/uploads",
  "out": "/mnt/user-data/outputs/result.gif",
  "height": 620,
  "crop": [250, 300, 1760, 2230],

  "parts": {
    "head": "머리.png", "body": "몸통.png",
    "armC_L": "가운데로_모은_왼팔.png", "armC_R": "가운데로_모은_오른팔.png",
    "armUp_R": "쭉_뻗은_오른쪽_팔.png", "armDn_L": "쭉_뻗은_왼쪽_팔.png",
    "armH_L": "가로_왼팔.png", "armH_R": "가로_오른팔.png",
    "legC_L": "쭈그린_왼다리.png", "legC_R": "쭈그린_오른다리.png",
    "legE_L": "뻗은_왼다리.png", "legE_R": "뻗은_오른다리.png"
  },
  "head": "head", "body": "body",

  "frames": [
    {"arms":["armC_L","armC_R"],"legs":["legC_L","legC_R"],
     "body_dy":72,"legs_dy":10,"head_dy":50,"ms":150},
    {"arms":["armDn_L","armUp_R"],"legs":["legE_L","legE_R"],
     "body_dy":-40,"legs_dy":-40,"head_dy":2,"ms":110},
    {"arms":["armH_L","armH_R"],"legs":["legE_L","legE_R"],
     "body_dy":-40,"legs_dy":-40,"head_dy":2,"ms":110,"arms_behind":true}
  ],

  "background": {
    "sprites": {"node":"번개노드.png","star":"로고.png"},
    "size":150, "cols":5, "rows":6, "opacity":0.30, "wobble":22
  },
  "mascots": [{"file":"clawd.png","size":420,"right":40,"bottom":30,"hop":14,"wobble":8}]
}
```

## 필드 의미

| 필드 | 설명 |
|---|---|
| `crop` | 원본 캔버스에서 잘라낼 영역 [x0,y0,x1,y1]. 배경 여백은 여기서 확보 |
| `body_dy` | 몸통+팔+머리 세로 이동. **접합 보정의 주 수단** |
| `legs_dy` | 다리 세로 이동. 웅크린 비트에서는 `body_dy`보다 훨씬 작게 |
| `head_dy` | `body_dy`에 **더해지는** 값. 클수록 목이 파묻힘 |
| `arms_behind` | true면 팔이 몸통 뒤 (가로로 뻗는 포즈에 사용) |
| `ms` | 그 프레임 노출 시간 |

## 값 잡는 요령

- 웅크림: `body_dy` 크게(+60~80), `legs_dy` 작게(+5~15), `head_dy` +45~55
- 뻗기: `body_dy` = `legs_dy` (같이 움직여야 골반이 안 벌어짐), `head_dy` 0~10
- 바운스 1왕복 = 뻗기 포즈로 4프레임 (위-아래-위-아래), 진폭은 두 번째가 작게
