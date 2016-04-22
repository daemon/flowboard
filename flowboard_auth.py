import base64
from functools import reduce
import hashlib
import pymongo
import random
import re

"""
Contains username, password, and email validation routines
"""
class Validator:
  user_rgx = re.compile("^[ -~]{2}[ -~]*$")
  email_rgx = re.compile("^[ -~]+@[ -~]+\\.\\w+$")

  """
  Checks if username is valid--contains at least 2 printable characters
  """
  @staticmethod
  def user_valid(user):
    return re.match(Validator.user_rgx, user.strip())

  """
  Roughly checks if the email is of name@domain.tld format
  """
  @staticmethod
  def email_valid(email):
    return re.match(Validator.email_rgx, email.strip())

  """
  Determines if password is valid--contains at least 10 characters, has lower/upper/numeric chars
  """
  @staticmethod
  def password_valid(password):
    response = Validator()
    response.valid_len = len(password) >= 10
    response.has_lower = False
    response.has_upper = False
    response.has_numeric = False
    for c in password:
      response.has_lower = response.has_lower or c.islower()
      response.has_upper = response.has_upper or c.isupper()
      response.has_numeric = response.has_numeric or c.isdigit()
    response.__bool__ = lambda: response.has_lower and response.has_upper and response.has_numeric and response.valid_len
    return response

"""
Basic hash function for flowboard
"""
def sha256x2(password, salt):
  image1 = ''.join([hashlib.sha256(password.encode()).hexdigest(), salt])
  image2 = base64.b64encode(hashlib.sha256(image1.encode()).digest())
  return image2

class AuthDatabase:
  status_ok = 1
  status_name_dup = 2
  status_email_dup = 4
  status_bad = 8
  def __init__(self, client):
    self.client = client
    self.users = client.db.users
    try:
      self.users.create_index("name", unique=True)
      self.users.create_index("email", unique=True)
    except:
      raise Exception("Couldn't create indices on users")

  """
  Registers a user based on provided form data. Returns an integral value with status_ok, status_name_dup, or status_email_dup bits
  set depending on outcome
  """
  def create_user(self, form_data):
    ret = self.status_bad
    if self.users.find_one({"name": form_data.user.strip()}):
      ret |= self.status_name_dup
    if self.users.find_one({"email": form_data.email}):
      ret |= self.status_email_dup
    if ret != self.status_bad:
      return ret
    salt = ''.join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789$!@#$%^&*()") for _ in range(8))
    try:
      hash64 = sha256x2(form_data.password, salt).decode("utf-8")
      self.users.insert_one({"name": form_data.user, "email": form_data.email, "password": hash64, "salt": salt})
      return self.status_ok
    except:
      return ret

"""
Wrapper/adapter between database and front end.
"""
class AuthService:
  def __init__(self, database):
    self.database = database

  """
  Attempts to register a user. Returns dictionary response suitable for conversion to JSON
  """
  def register(self, form_data):
    if not form_data.valid():
      return {"success": False, "password_valid": form_data.password_valid, 
        "email_valid": form_data.email_valid, "user_valid": form_data.user_valid}
    response = self.database.create_user(form_data)
    register_response = {"success": response & AuthDatabase.status_ok == AuthDatabase.status_ok}
    if not response & AuthDatabase.status_ok:
      register_response["name_dup"] = response & AuthDatabase.status_name_dup == AuthDatabase.status_name_dup
      register_response["email_dup"] = response & AuthDatabase.status_email_dup == AuthDatabase.status_email_dup
    return register_response

  class FormData:
    def __init__(self, user, password, email):
      self.user = user
      self.password = password
      self.email = email
      self.user_valid = Validator.user_valid(self.user) is not None
      self.password_valid = Validator.password_valid(self.password).__bool__()
      self.email_valid = Validator.email_valid(self.email) is not None

    def valid(self):
      return self.user_valid and self.password_valid and self.email_valid
