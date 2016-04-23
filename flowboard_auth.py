import base64
import datetime
from functools import reduce
import hashlib
import json
import pymongo
import random
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
More secure random.choice generator
"""
def sec_random_gen(length, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789$!@#$%^&*()"):
  return ''.join(random.SystemRandom().choice(alphabet) for _ in range(length))

"""
Basic hash function for flowboard
"""
def sha256x2(password, salt):
  image1 = ''.join([hashlib.sha256(password.encode()).hexdigest(), salt])
  image2 = base64.b64encode(hashlib.sha256(image1.encode()).digest())
  return image2

def generate_session_id():
  return sec_random_gen(32)

"""
Checks if user is human via reCAPTCHA service
"""
def recaptcha_valid(recaptcha_secret, recaptcha_response, ip):
  fields = {'response': recaptcha_response, 'remoteip': ip, 'secret': recaptcha_secret}
  request = Request("https://www.google.com/recaptcha/api/siteverify", urlencode(fields).encode())
  response = urlopen(request).read().decode()
  return json.loads(response)["success"]

class AuthDatabase:
  status_ok = 1
  status_name_dup = 2
  status_email_dup = 4
  status_bad = 8
  def __init__(self, client):
    self.client = client
    self.users = client.db.users
    self.sessions = client.db.sessions
    try:
      self.users.create_index("name", unique=True)
      self.users.create_index("email", unique=True)
      self.sessions.create_index("session_id")
      self.sessions.create_index("last_accessed", expireAfterSeconds=600000)
    except:
      raise Exception("Couldn't create indices on database")

  def find_user_by_ssid(self, session_id):
    session = self.sessions.find_one({"session_id": session_id})
    if not session:
      return None
    user = self.users.find_one({"_id": session["user_id"]})
    return user

  """
  Attempts to authenticate a user given name and password. Returns session ID string on success, None otherwise
  """
  def login_by_name(self, name, password):
    user = self.users.find_one({"name": name})
    if not user:
      return None
    salt = user["salt"]
    if not salt:
      return None
    sha256x2_hash = sha256x2(password, salt).decode("utf-8")
    if sha256x2_hash == user["password"]:
      sid = generate_session_id()
      self.sessions.insert_one({"user_id": user["_id"], "last_accessed": datetime.datetime.utcnow(), "session_id": sid})
      return sid
    return None

  """
  Attempts to authenticate user given session id. Returns user ID on success, None otherwise
  """
  def login_by_session_id(self, session_id):
    session = self.sessions.find_one_and_update({"session_id": session_id}, {"$set": {"last_accessed": datetime.datetime.utcnow()}}, upsert=False)
    if session is None:
      return None
    return str(session["user_id"])

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
    salt = sec_random_gen(8)
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

  """
  Attempts to authenticate a user. Returns dictionary response suitable for conversion to JSON
  """
  def login(self, user=None, password=None, session_id=None):
    if session_id:
      response = self.database.login_by_session_id(session_id)
      if response:
        return {"success": True, "user_id": response}
    else:
      response = self.database.login_by_name(user, password)
      if response:
        return {"success": True, "session_id": response}
    return {"success": False}

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
