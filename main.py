from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (CarouselColumn, CarouselTemplate, ImageMessage, AudioMessage, 
                            MessageEvent, TemplateSendMessage, TextMessage,
                            TextSendMessage, URITemplateAction)

import config

from google.cloud import vision
from google.cloud.vision import types
from google.cloud import storage

PROJECT_ID = config.PROJECT_ID
CLOUD_STORAGE_BUCKET = config.CLOUD_STORAGE_BUCKET

app = Flask(__name__)


line_bot_api = LineBotApi(config.CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(config.CHANNEL_SECRET)



# [START upload_file]
def upload_file(file_stream, filename, content_type):
    """
    Uploads a file to a given Cloud Storage bucket and returns the public url
    to the new object.
    """
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(CLOUD_STORAGE_BUCKET)

    if content_type=='image/jpg':
        file_fullname = filename+'.jpg'

    blob = bucket.blob(file_fullname)

    blob.upload_from_string(
        file_stream,
        content_type=content_type)

    url = 'gs://{}/{}'.format(CLOUD_STORAGE_BUCKET, file_fullname)

    return url
# [END upload_file]


@app.route("/auto_ocr", methods=['POST'])
def auto_ocr():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)

    # handle webhook body
    try:
        handler.handle(body, signature)

    except InvalidSignatureError as e:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    messages = [
        #TextSendMessage(text=text),
        TextSendMessage(text='画像を送ってみてね!含まれている文字を結果として返すよ。'),
    ]

    reply_message(event, messages)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):

    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    response_text = ""

    image = message_content.content


    try:
        # Image Upload
        image_url = upload_file(image,message_id,"image/jpg")

        if image_url:
            try:
                client = vision.ImageAnnotatorClient()
                response = client.annotate_image({
                    'image': {'source': {'image_uri': image_url}},
                    'features': [{'type': vision.enums.Feature.Type.TEXT_DETECTION}],
                    })

                texts = response.text_annotations
                response_text += texts[0].description

                messages = [
                        TextSendMessage(text='結果は、下記です。'),
                        TextSendMessage(text=response_text),
                        ]
        
                reply_message(event, messages)

            except Exception as e:
                messages = [
                        TextSendMessage(text='Error: '+str(e)),
                        ]
                reply_message(event, messages)
        

    except Exception as e:
        messages = [
                TextSendMessage(text='Error: '+str(e)),
                ]
        reply_message(event, messages)


def reply_message(event, messages):
    line_bot_api.reply_message(
        event.reply_token,
        messages=messages,
    )

