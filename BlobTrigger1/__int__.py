import azure.functions as func
import logging

app = func.FunctionApp()

@app.blob_trigger(
    arg_name="myblob",
    path="videouploadcontainer/{name}",
    connection="CUSTOM_BLOB_STORAGE"
)
@app.function_name(name="process_blob_video")
def process_blob_video(myblob: func.InputStream, name: str):
    logging.info(f"🚀 Triggered by: {name}")
    logging.info(f"📏 Size: {myblob.length} bytes")
