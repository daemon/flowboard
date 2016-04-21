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