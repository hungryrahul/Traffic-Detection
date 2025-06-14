from ultralytics import YOLO
import cv2
import pandas as pd
import math
import azure.functions as func
import logging
import os
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", 
                  path="trafficmanagementcontainer/{name}",
                  connection="trafficdetection_STORAGE")
def TrafficDetectionBlobTrigger(myblob: func.InputStream, name: str):
    try:
        logging.info(f"Processing blob: {name} ({myblob.length} bytes)")
        temp_video_path = f"/tmp/{name}"

        with open(temp_video_path, "wb") as f:
            f.write(myblob.read())

        model_path = os.path.join(os.path.dirname(__file__), "yolov8n.pt")
        if not os.path.exists(model_path):
            logging.error("❌ YOLO model not found.")
            return

        model = YOLO(model_path)

        cap = cv2.VideoCapture(temp_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        pixel_to_meter = 0.05

        results = model.track(
            source=temp_video_path,
            show=False,
            persist=True,
            save=False,
            tracker="bytetrack.yaml"
        )

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

        frame_counts = df.groupby("frame").size().reset_index(name="vehicle_count")
        frame_counts["congestion"] = frame_counts["vehicle_count"].apply(lambda x: "High" if x > 10 else "Normal")
        congestion_map = dict(zip(frame_counts["frame"], frame_counts["congestion"]))

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

        result_df = pd.DataFrame(rows)
        csv_path = f"/tmp/{name}_vehicle_data.csv"
        result_df.to_csv(csv_path, index=False)

        logging.info("✅ Final CSV saved.")
        logging.info(result_df.head().to_string())

        # Upload CSV to Blob
        blob_conn_str = os.environ["trafficdetection_STORAGE"]
        blob_service_client = BlobServiceClient.from_connection_string(blob_conn_str)
        result_container = "csv-results"

        blob_client = blob_service_client.get_blob_client(
            container=result_container, 
            blob=f"{name}_vehicle_data.csv"
        )
        with open(csv_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        logging.info(f"✅ CSV uploaded to blob container '{result_container}' as {name}_vehicle_data.csv")

    except Exception as e:
        logging.error(f"❌ Function error: {e}")
