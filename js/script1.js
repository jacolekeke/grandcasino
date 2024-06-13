$(".dyn-btn.register, .dyn-text.register").click(function(){
	$(".dyn-btn.register").hide();
	$(".dyn-btn.login").show();
	
	$(".form-content.login").style.display = "none";
	$(".form-content.register").style.display = "block";
});
$(".dyn-btn.login, .dyn-text.login").click(function(){
	$(".dyn-btn.register").show();
	$(".dyn-btn.login").hide();
	
	$(".form-content.login").style.display = "block";
	$(".form-content.register").style.display = "none";
});

if ($(window).width() >= 768) {
	new PerfectScrollbar(".form-content.register .form-elements", {
		wheelSpeed: 0.5,
		wheelPropagation: true
	});
}
