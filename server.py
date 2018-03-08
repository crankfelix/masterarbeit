from flask import Flask, json, request, abort, make_response
import base64
import uuid

app = Flask(__name__)

@app.route("/")
def index():
	return "Hallo"

@app.route("/api/v1/data",methods=["GET"])
def return_data():
	with open("C:\\Users\\Felix\\Pictures\\IMG_2696.JPG","rb") as picture:
		
		retValue = base64.b64encode(picture.read())
		return retValue

@app.route("/api/v1/model",methods=["POST"])
def accept_model():
	if not request.json:
		abort(400)
	with open(str(uuid.uuid4())+".json","w+") as file:
		file.write(str(request.json))

	return "nice",201


if __name__ == "__main__":
	app.run(debug=True)