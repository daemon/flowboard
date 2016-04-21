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
  $(".bg-cover").animate({"opacity": 0.4}, "slow");
  $("#login-container").css("visibility", "visible");
  $("#login-container").animate({"opacity": 1}, "slow");
  $("#login-user").focus();
  loginExpanded = true;
});

$("#signup-btn").click(function() {
  $(".bg-cover").css("visibility", "visible");
  $(".bg-cover").animate({"opacity": 0.4}, "slow");
  $("#signup-container").css("visibility", "visible");
  $("#signup-container").animate({"opacity": 1}, "slow");
  $("#signup-email").focus();
  signupExpanded = true;
});

$(".bg-cover").click(function() {
  if (loginExpanded) {
    $(".bg-cover").css("opacity", 0);
    $(".bg-cover").css("visibility", "hidden");
    $("#login-container").css("visibility", "hidden");
    $("#login-container").css("opacity", 0);
    $("#login-container input").val("");
    $("#login-container input[type=submit]").val("Login");
    loginExpanded = false
  } else if (signupExpanded) {
    $(".bg-cover").css("opacity", 0);
    $(".bg-cover").css("visibility", "hidden");
    $("#signup-container").css("visibility", "hidden");
    $("#signup-container").css("opacity", 0);
    $("#signup-container input").val("");
    $("#signup-container input[type=submit]").val("Sign up");
    signupExpanded = false
  }
});