import json
import os
import logging
from flask import Flask, request
from watson_developer_cloud import VisualRecognitionV3
from watson_developer_cloud import watson_service

app = Flask(__name__, static_url_path='')
app.config['PROPAGATE_EXCEPTIONS'] = True
logging.basicConfig(level=logging.FATAL)
port = os.getenv('VCAP_APP_PORT', '5000')

# Global variables for credentials
apikey = '' #'Pisle8UwpxlbBiP36uJDxfi0LbC4L_92ZEnmcX922iVh'
classifier_id = '' #'waste_1340454629'


# Set Classifier ID
def set_classifier():
    app.logger.info('set_classifier')
    visual_recognition = VisualRecognitionV3('2018-03-19', iam_apikey=apikey)
    classifiers = visual_recognition.list_classifiers(verbose=True).get_result()
    print(json.dumps(classifiers, indent=2))
    #app.logger.error(json.dumps(visual_recognition.list_classifiers().get_result()))
    for classifier in classifiers['classifiers']:
        if classifier['name'] == 'waste':
            if classifier['status'] == 'ready':
                print(classifier)
                return classifier['classifier_id']
            else:
                return ''
    create_classifier()
    return ''


# Create custom waste classifier
def create_classifier():
    app.logger.info('create_classifier')
    visual_recognition = VisualRecognitionV3('2018-03-19', iam_apikey=apikey)
    with open('./resources/landfill.zip', 'rb') as landfill, open(
        './resources/recycle.zip', 'rb') as recycle, open(
            './resources/compost.zip', 'rb') as compost, open(
                './resources/negative.zip', 'rb') as negative:
        visual_recognition.create_classifier(
            'waste',
            Landfill_positive_examples=landfill,
            Recycle_positive_examples=recycle,
            Compost_positive_examples=compost,
            negative_examples=negative)
    return ''

# https://www.ibm.com/watson/developercloud/visual-recognition/api/v3/python.html?python#authentication

# API destination
@app.route('/api/sort', methods=['POST'])
def sort():
    try:
        images_file = request.files.get('images_file', '')
        visual_recognition = VisualRecognitionV3('2018-03-19',
                                                 iam_apikey=apikey)
        app.logger.info("received file")
        print('received file')
        global classifier_id
        if classifier_id == '':
            classifier_id = set_classifier()
            if classifier_id == '':
                app.logger.info('classifier_id = %s', classifier_id)
                return json.dumps(
                    {"status code": 500, "result": "Classifier not ready",
                        "confident score": 0})
        # parameters = json.dumps({'classifier_ids': [classifier_id]})
        url_result = visual_recognition.classify(images_file=images_file,classifier_ids=[classifier_id]).get_result()
                                                 #parameters=parameters).get_result()
        app.logger.info('url_result %s', url_result)
        print('url_result %s', url_result)
        if len(url_result["images"][0]["classifiers"]) < 1:
            return json.dumps(
                    {"status code": 500, "result": "Image is either not "
                        "a waste or it's too blurry, please try it again.",
                        "confident score": 0})
        list_of_result = url_result["images"][0]["classifiers"][0]["classes"]
        app.logger.info('analyzing list of results')
        print('analyzing list of results')
        result_class = ''
        result_score = 0
        for result in list_of_result:
            app.logger.info('result: %s', result)
            print('result: ', result)
            if result["score"] >= result_score:
                result_score = result["score"]
                result_class = result["class"]
        return json.dumps(
            {"status code": 200, "result": result_class,
                "confident score": result_score})
    except Exception as e:
        logging.exception("message")
        logging.error('error')
        app.logger.error('exception')
        app.logger.error(e)
        print(e)
        return json.dumps(
            {"status code": 500, "result": "Not an image",
                "confident score": 0})


# Default frontend page.
@app.route('/')
def default():
    return ''


if __name__ == "__main__":
    visual_creds = watson_service.load_from_vcap_services(
        'watson_vision_combined')
    apikey = visual_creds['apikey']
    classifier_id = set_classifier()
    app.run(host='0.0.0.0', port=int(port), debug=True)
