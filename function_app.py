import azure.functions as func


app = func.FunctionApp()

@app.blob_trigger(
    arg_name="myblob",
    path="videouploadcontainer/{name}",
    connection="AzureWebJobsStorage"
)
@app.function_name(name="process_blob_video")
def process_blob_video(myblob: func.InputStream, name: str):
    import logging
    logging.info(f"🚀 Triggered by: {name}")
    logging.info(f"📏 Size: {myblob.length} bytes")
