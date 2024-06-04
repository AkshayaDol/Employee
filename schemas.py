# schemas.py
from marshmallow import Schema, fields, validates, ValidationError
import re

class EmployeeProfileSchema(Schema):
    EmployeeID = fields.Int(required=True)
    FirstName = fields.Str(required=True)
    LastName = fields.Str(required=True)
    StartDate = fields.Date(required=True, format="%Y-%m-%d")  # Ensure date is in 'YYYY-MM-DD' format
    Country = fields.Str(required=True)

    @validates('EmployeeID')
    def validate_employee_id(self, value):
       # if not re.match(r'^\d{7}$', value):
        if 10000000 < value < 1000000:
            raise ValidationError('EmployeeID must be exactly 7 digits.')

    @validates('Country')
    def validate_country(self, value):
        if not re.match(r'^[A-Z]{2}$', value):
            raise ValidationError('Country must be a 2-letter ISO-3166 code.')
