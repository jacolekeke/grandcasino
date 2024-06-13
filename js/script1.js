$(".dyn-btn.register, .dyn-text.register").click(function(){
	$(".dyn-btn.register").hide();
	$(".dyn-btn.login").show();
	
	$(".form-content.login").hide();
	$(".form-content.register").show();
});
$(".dyn-btn.login, .dyn-text.login").click(function(){
	$(".dyn-btn.register").show();
	$(".dyn-btn.login").hide();
	
	$(".form-content.login").show();
	$(".form-content.register").hide();
});

if ($(window).width() >= 768) {
	new PerfectScrollbar(".form-content.register .form-elements", {
		wheelSpeed: 0.5,
		wheelPropagation: true
	});
}