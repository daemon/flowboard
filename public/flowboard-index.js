var expanded = false;
$(document).mouseup(function() {
  if (expanded && document.activeElement.id !== "topic-body" && document.activeElement.id !== "topic-title")
  {
    $("#topic-form").animate({"height": "49px"}, "fast");
    expanded = false;
  }
});

$("#topic-title").click(function() {
  if (!expanded)
  {
    $("#topic-form").animate({"height": "195px"}, "fast");
    expanded = true;
  }
});

var loginExpanded = false;
var signupExpanded = false;
$("#login-btn").click(function() {
  $(".bg-cover").css("visibility", "visible");
  $(".bg-cover").fadeTo(500, 0.4);
  $("#login-container").css("visibility", "visible");
  $("#login-container").fadeTo(500, 1);
  $("#login-user").focus();
  loginExpanded = true;
});

$("#signup-btn").click(function() {
  $(".bg-cover").css("visibility", "visible");
  $(".bg-cover").fadeTo(500, 0.4);
  $("#signup-container").css("visibility", "visible");
  $("#signup-container").fadeTo(500, 1);
  $("#signup-email").focus();
  signupExpanded = true;
});

$(".bg-cover").click(function() {
  if (loginExpanded) {
    $(".bg-cover").fadeOut();
    $("#login-container").fadeOut();
    $("#login-container input").val("");
    $("#login-container input[type=submit]").val("Login");
    loginExpanded = false
  } else if (signupExpanded) {
    $(".bg-cover").fadeOut();
    $("#signup-container").fadeOut();
    $("#signup-container input").val("");
    $("#signup-container input[type=submit]").val("Sign up");
    signupExpanded = false
  }
});

var signupErrorTxt = "<span style='display: block; width: 100%; text-align: center;'>";

var cssFormValidate = function(formElement, valid) {
  if (valid)
    $(formElement).css("border-bottom", "1px solid #AAA");
  else
    $(formElement).css("border-bottom", "1px solid red");
};

var doSignup = function() {
  var socket = new WebSocket("wss://flowboard.rocketeer.net:9001");
  var email = $("#signup-email").val()
  var user = $("#signup-user").val()
  var password = $("#signup-password").val()
  var recaptchaResponse = $("#g-recaptcha-response").val();
  var signupForm = $("#signup-form");  
  signupForm.hide();
  cssFormValidate("#signup-password", true);
  cssFormValidate("#signup-email", true);
  cssFormValidate("#signup-user", true);
  var signupErrorNotify = $("#signup-error-notify");
  signupErrorNotify.html(signupErrorTxt + "Signing up...</span>");
  socket.onmessage = function(event) {
    response = JSON.parse(event.data);
    msg = "";
    socket.close();
    signupErrorNotify.html("");
    signupForm.show();
    if (response.hasOwnProperty("password_valid")) {
      cssFormValidate("#signup-password", response["password_valid"]);
      cssFormValidate("#signup-email", response["email_valid"]);
      cssFormValidate("#signup-user", response["user_valid"]);
      if (!response["password_valid"])
        msg += "Password needs to be at least 10 characters long with numbers, lowercase, and uppercase. ";
      if (!response["user_valid"])
        msg += "Username must be at least 2 printable characters long.";
    } else if (response.hasOwnProperty("name_dup")) {
      if (response["name_dup"] || response["email_dup"])
        msg = "Name and/or email are already taken. ";
      cssFormValidate("#signup-email", !response["email_dup"]);
      cssFormValidate("#signup-user", !response["name_dup"]);
    }
    if (msg !== "")
      signupErrorNotify.html(signupErrorTxt + msg + "</span>");
    else if (response["success"])
    {
      signupForm.hide();
      signupErrorNotify.html(signupErrorTxt + "Success!</span>");
      window.setTimeout(function() {$(".bg-cover").click()}, 2500);
    }
  }

  socket.onopen = function(e) {
    socket.send(JSON.stringify({'email': email, 'user': user, 'password': password, 'recaptcha_response': recaptchaResponse}));
  }
  return false;
};