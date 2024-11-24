from pydantic import BaseModel
from tortoise import fields
from tortoise.models import Model

class Skill(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)

class Employer(Model):
    id = fields.IntField(pk=True)
    tg_id = fields.IntField(unique=True)
    tg_username = fields.CharField(max_length=50, null=True)
    name = fields.CharField(max_length=30, null=True)
    surname = fields.CharField(max_length=30, null=True)
    email = fields.CharField(max_length=100, null=True)
    phone = fields.CharField(max_length=30, null=True)

class Employee(Model):
    id = fields.IntField(pk=True)
    tg_id = fields.IntField(unique=True)
    tg_username = fields.CharField(max_length=50, null=True)
    name = fields.CharField(max_length=30, null=True)
    surname = fields.CharField(max_length=30, null=True)
    email = fields.CharField(max_length=100, null=True)
    phone = fields.CharField(max_length=30, null=True)
    skills = fields.ManyToManyField('models.Skill', related_name='employees')
    cv_url = fields.CharField(max_length=300, null=True)
    expected_salary = fields.IntField(null=True)
    city = fields.CharField(max_length=30, null=True)


class SendMessageRequest(BaseModel):
    chat_id: int
    text: str