import logging

import azure.functions as func

def main(myblob: func.InputStream):
    logging.info(f"🚀 Blob trigger function processed blob: {myblob.name}")
    logging.info(f"📏 Blob size: {myblob.length} bytes")
