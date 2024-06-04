import os

from flask import Blueprint, request, jsonify, send_file
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from schemas import EmployeeProfileSchema
from marshmallow import ValidationError
from io import BytesIO
import functools

employee_bp = Blueprint('employee_bp', __name__)

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_default_region = os.getenv('AWS_DEFAULT_REGION')

# Create a session using environment variables
boto3_session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_default_region
)

# dynamodb = boto3_session.resource('dynamodb', region_name=aws_default_region)
# boto3_session = boto3.Session(profile_name="Akshaya")
dynamodb = boto3_session.resource('dynamodb', region_name="us-west-2")
s3 = boto3_session.client('s3', region_name="us-west-2")
credentials_table = dynamodb.Table('Client_Credentials')

# Set the table and bucket names
DYNAMODB_TABLE_NAME = 'Employee'
S3_BUCKET_NAME = 'employeephoto'

def validate_token(access_token):
    try:
        response = credentials_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('access_token').eq(access_token)
        )
        if response['Items']:
            return True
        return False
    except ClientError as e:
        print(f"ClientError: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

def token_required(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'message': 'Token is missing or invalid!'}), 401
        token = auth.split(' ')[1]
        if not validate_token(token):
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return wrap

@employee_bp.route('/<int:employee_id>/profile', methods=['GET', 'POST'])
@token_required
def profile(employee_id):
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    profile_schema = EmployeeProfileSchema()

    if request.method == 'POST':
        data = request.get_json()
        try:
            # Add employee_id to the data for validation
            data['EmployeeID'] = employee_id
            # Validate and deserialize input
            print(f'Data: {data}')
            profile_data = profile_schema.load(data)
            print(f'Profile data: {profile_data}')
            # Save the valid profile data to DynamoDB
            table.put_item(Item=data)
            return jsonify({'message': 'Profile created successfully'}), 201
        except ValidationError as err:
            return jsonify(err.messages), 400
        except (NoCredentialsError, PartialCredentialsError) as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'GET':
        try:
            response = table.get_item(Key={'EmployeeID': employee_id})
            if 'Item' in response:
                return jsonify(response['Item']), 200
            else:
                return jsonify({'error': 'Employee not found'}), 404
        except (NoCredentialsError, PartialCredentialsError) as e:
            return jsonify({'error': str(e)}), 500

@employee_bp.route('/<int:employee_id>/photo', methods=['GET', 'POST'])
@token_required
def photo(employee_id):
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)

    if request.method == 'POST':
        if 'photo' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        try:
            # Upload the file to S3
            s3.put_object(Bucket=S3_BUCKET_NAME, Key=f'{employee_id}.jpg', Body=file)

            # Update the DynamoDB record with the S3 URL
            s3_url = f'https://{S3_BUCKET_NAME}.s3.amazonaws.com/{employee_id}.jpg'
            table.update_item(
                Key={'EmployeeID': employee_id},
                UpdateExpression='SET PhotoURL = :val1',
                ExpressionAttributeValues={':val1': s3_url}
            )

            return jsonify({'message': 'Photo uploaded and profile updated successfully'}), 201
        except (NoCredentialsError, PartialCredentialsError) as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'GET':
        try:
            file_obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=f'{employee_id}.jpg')
            return send_file(BytesIO(file_obj['Body'].read()), mimetype='image/jpeg')
        except s3.exceptions.NoSuchKey:
            return jsonify({'error': 'Photo not found'}), 404
        except (NoCredentialsError, PartialCredentialsError) as e:
            return jsonify({'error': str(e)}), 500

