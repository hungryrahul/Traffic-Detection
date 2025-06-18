import azure.functions as func
import logging

app = func.FunctionApp()

@app.blob_trigger(
    arg_name="myblob",
    path="videouploadcontainer/{name}",
    connection="AzureWebJobsStorage"
)
@app.function_name(name="log_blob_name")
def log_blob_name(myblob: func.InputStream, name: str):
    logging.info(f"🚀 Triggered by: {name}")
    logging.info(f"📏 Size: {myblob.length} bytes")
