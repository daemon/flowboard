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
    $("#topic-form").animate({"height": ($("#topic-body").outerHeight() + $("#new-post-submit").outerHeight() + 49) + "px"}, "fast");
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

var createNotifyMsg = function(message) {
  return "<span style='display: block; width: 100%; text-align: center;'>" + message + "</span>";
};

var cssFormValidate = function(formElement, valid) {
  if (valid)
    $(formElement).css("border-bottom", "1px solid #AAA");
  else
    $(formElement).css("border-bottom", "1px solid red");
};

var doLogin = function() {
  var socket = new WebSocket("wss://flowboard.rocketeer.net:9001");
  var user = $("#login-user").val();
  var password = $("#login-password").val();
  var loginForm = $("#login-form");
  var loginNotify = $("#login-error-notify");
  loginForm.hide();
  loginNotify.html(createNotifyMsg("Logging in..."));
  socket.onmessage = function(event) {
    var response = JSON.parse(event.data);
    if (response["success"]) {
      var expiryDate = new Date();
      expiryDate.setDate(expiryDate.getDate() + 14);
      document.cookie = "ssid=" + response["session_id"] + "; expires=" + expiryDate.toISOString() + ";";
      loginNotify.html(createNotifyMsg("Success!"));
      window.setTimeout(function() { window.location = "/"; }, 2000);
    } else {
      loginNotify.html(createNotifyMsg("Invalid credentials."));
      loginForm.show();
    }
    socket.close();
  }

  socket.onopen = function(event) {
    socket.send(JSON.stringify({'user': user, 'password': password, 'req_type': 1}));
  }

  return false;
}

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
  signupErrorNotify.html(createNotifyMsg("Signing up..."));
  socket.onmessage = function(event) {
    var response = JSON.parse(event.data);
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
    } else if (response.hasOwnProperty("captcha_valid")) {
      msg = "CAPTCHA invalid.";
    }
    if (msg !== "")
      signupErrorNotify.html(createNotifyMsg(msg));
    else if (response["success"])
    {
      signupForm.hide();
      signupErrorNotify.html(createNotifyMsg("Success! You may now login."));
      window.setTimeout(function() {$(".bg-cover").click()}, 2500);
    }
  }

  socket.onopen = function(e) {
    socket.send(JSON.stringify({'req_type': 0, 'email': email, 'user': user, 'password': password, 'recaptcha_response': grecaptcha.getResponse()}));
    grecaptcha.reset();
  }
  return false;
};

var createPost = function(id, title, author, message, nReplies) {
  return "<article id='" + id + "'>\
    <div class='top-bar'>\
      <span class='title' title='" + (new Date()).toISOString() + "'>" + title + "</span><span class='author'>" + author + "</span>\
    </div>\
      <p><span>" + message + "</span></p>\
    <div class='bottom-bar'><a id='link-" + id + "' class='reply' href='javascript:void(0)'>" + nReplies + " replies</a></div>\
  </article>";
}

var NEW_THREAD = 0;
var NEW_REPLY_NOTIFY = 1;
var postSocket = new WebSocket("wss://flowboard.rocketeer.net:9001");
var checkTaskId = false;

var checkPostSocket = function() {
  if (postSocket.readyState === undefined || postSocket.readyState > 1) {
    postSocket.close();
    postSocket = new WebSocket("wss://flowboard.rocketeer.net:9001");
    setupPostSocket(postSocket);
  }
};

var createReply = function(author, message) {
  return "<article style='padding-left: 20px; width: 800px; border-bottom: none;'>\
        <span style='word-wrap: break-word; width: 800px;'><strong>" + author + "</strong>: " + message + "</span></article>";
};

var setupPostSocket = function(socket) {
  socket.onopen = function(event) {
    if (checkTaskId !== false)
      clearInterval(checkTaskId);
    socket.send('{"req_type": 2}');
    checkTaskId = setInterval(checkPostSocket, 15000);
    for (i in subscribedTopics) {
      socket.send(JSON.stringify({req_type: 5, post_id: subscribedTopics[i]}));
    }
  };

  socket.onmessage = function(event) {
    data = JSON.parse(event.data);
    if (data["post_type"] == NEW_THREAD) {
      var title = data["title"];
      var message = data["message"];
      var author = data["author"];
      var id = data["post_id"];
      var nReplies = data["n_replies"];
      var posts_section = $("#posts");
      posts_section.prepend(createPost(id, title, author, message, nReplies))
      $("#link-" + id).click(function() { expandReplies(id); });
      $("#" + id + " span").css("background-color", "yellow").animate({backgroundColor: "#EEE"}, 1500);
    } else if (data["post_type"] == NEW_REPLY_NOTIFY) {
      var message = data["message"];
      var author = data["author"];
      $("#reply-container-" + data["post_id"]).append(createReply(author, message))
        .scrollTop($("#reply-container-" + data["post_id"] + " article").length * 50);
    }
  };
};

setupPostSocket(postSocket);

var doReply = function(id) {
  var message = $("#reply-" + id).val();
  $("#reply-" + id).val("").focus();
  var request = JSON.stringify({req_type: 4, post_id: id, message: message, ssid: getCookie("ssid").slice(1, -1)});
  var socket = new WebSocket("wss://flowboard.rocketeer.net:9001");
  socket.onopen = function(e) {
    socket.send(request);
  }

  socket.onmessage = function(e) {
    socket.close();
  }
  return false;
};

var subscribedTopics = [];

// todo toggle replies
var expandReplies = function(post_id) {
  var post = $("#" + post_id);
  if (!post.attr("data-expanded")) {
    subscribedTopics.push(post_id);
    postSocket.send(JSON.stringify({req_type: 5, post_id: post_id}));
    post.append("<span style='text-align: center; width: 100%;'>Loading...</span>");
    post.append("<section class='replies' id='reply-container-" + post_id + "'></section><form autocomplete='off'\
      onsubmit=\"return doReply('" + post_id + "');\" id='form-" + post_id + "' style='margin-top:5px; width: 930px'>\
      <input placeholder='Message' id='reply-" + post_id + "' type='text' style='width: 760px;'>\
      <input id='reply-submit-" + post_id + "' type='submit' value='Submit' style='width: 140px;'></form>");
    var socket = new WebSocket("wss://flowboard.rocketeer.net:9001");
    socket.onopen = function(e) {
      socket.send(JSON.stringify({post_id: post_id, req_type: 6}));
    };

    socket.onmessage = function(e) {
      $("#" + post_id + " > span").remove();
      response = JSON.parse(e.data);
      if (!response["success"])
        return;
      var reply_container = $("#reply-container-" + post_id);
      for (i in response["replies"]) {
        author = response["replies"][i]["author"];
        message = response["replies"][i]["message"];
        reply_container.append(createReply(author, message));
      }
      reply_container.scrollTop($("#reply-container-" + post_id + " article").length * 50);
    }
  }
  post.attr("data-expanded", true);
};

$(".reply").each(function(index) {
  $(this).click(function() {
    expandReplies($(this).attr("data-reply-id"));
    $("#reply-" + $(this).attr("data-reply-id")).focus();
  });
});

var getCookie = function(cname) {
  var name = cname + "=";
  var ca = document.cookie.split(';');
  for(var i = 0; i <ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0)==' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0)
      return c.substring(name.length,c.length);
  }

  return "";
} 

$("#new-post-submit").click(function(e) {
  var title = $("#topic-title").val();
  var body = $("#topic-body").val();
  var ssid = getCookie("ssid").slice(1, -1);
  if (ssid === "")
    return;
  var ws = new WebSocket("wss://flowboard.rocketeer.net:9001");
  ws.onopen = function(event) {
    ws.send(JSON.stringify({"req_type": 3, "title": title, "message": body, "ssid": ssid}));
  };

  ws.onmessage = function(event) {
    var response = JSON.parse(event.data);
    if (response["success"]) {
      $("#topic-title").val("");
      $("#topic-body").val("");
    }
    ws.close();
  }
});