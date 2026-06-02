from ultralytics import YOLO

model = YOLO('best.pt')

# 학습된 알약 종류 확인
print("=== 학습된 알약 목록 ===")
print(model.names)

# 모델 기본 정보
print("\n=== 모델 정보 ===")
print(model.info())