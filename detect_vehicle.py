from ultralytics import YOLO
import cv2
import pandas as pd
import math

# Load YOLOv8
model = YOLO("yolov8n.pt")

# Load video
video_path = "test_video.mp4"
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
pixel_to_meter = 0.05

# Run tracking
results = model.track(
    source=video_path,
    show=False,
    persist=True,
    save=True,
    tracker="bytetrack.yaml"
)

# Step 1: Collect detections
detection_rows = []
frame_index = 0
for result in results:
    if result.boxes.id is not None:
        for i in range(len(result.boxes)):
            obj_id = int(result.boxes.id[i])
            cls_id = int(result.boxes.cls[i])
            label = model.names[cls_id]
            cx, cy = result.boxes.xywh[i][:2].tolist()

            detection_rows.append({
                "frame": frame_index,
                "id": obj_id,
                "label": label,
                "cx": cx,
                "cy": cy
            })
    frame_index += 1

df = pd.DataFrame(detection_rows)

# Step 2: Build congestion map (vehicle count per frame)
frame_counts = df.groupby("frame").size().reset_index(name="vehicle_count")
frame_counts["congestion"] = frame_counts["vehicle_count"].apply(lambda x: "High" if x > 10 else "Normal")

# Map: frame → congestion
congestion_map = dict(zip(frame_counts["frame"], frame_counts["congestion"]))

# Step 3: Aggregate vehicle info
rows = []
for obj_id in df["id"].unique():
    d = df[df["id"] == obj_id].sort_values("frame")
    if len(d) < 2:
        continue

    label = d["label"].iloc[0]
    entry_frame = d["frame"].iloc[0]
    exit_frame = d["frame"].iloc[-1]
    total_frames = exit_frame - entry_frame + 1
    time_sec = total_frames / fps

    x1, y1 = d[["cx", "cy"]].iloc[0]
    x2, y2 = d[["cx", "cy"]].iloc[-1]
    pixel_dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    meters = pixel_dist * pixel_to_meter
    speed_kmph = (meters / time_sec) * 3.6 if time_sec > 0 else 0.0

    # Use most frequent congestion tag during vehicle's time in frame
    congestion_list = [congestion_map.get(f, "Unknown") for f in d["frame"]]
    congestion = max(set(congestion_list), key=congestion_list.count)

    rows.append({
        "id": obj_id,
        "label": label,
        "entry_frame": entry_frame,
        "exit_frame": exit_frame,
        "total_frames": total_frames,
        "speed_kmph": round(speed_kmph, 2),
        "congestion": congestion
    })

# Step 4: Save to one CSV
result_df = pd.DataFrame(rows)
result_df.to_csv("final_vehicle_data.csv", index=False)

print("✅ Final CSV saved: final_vehicle_data.csv")
print(result_df.head())
