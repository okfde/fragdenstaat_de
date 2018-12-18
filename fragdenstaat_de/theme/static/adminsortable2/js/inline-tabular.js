/* Remove this file once is fixed: https://github.com/jrief/django-admin-sortable2/issues/217 */
django.jQuery(function($) {
	$("script.inline-tabular-config").each(function (i, config_element) {
		try {
			var config = JSON.parse(config_element.textContent);
		}
		catch (parse_error) {
			console.error("Configuration for a django-adminsortable2 inline-tabular form is invalid.");
		}

		// Note: This function signature changed in Django 2.1.
		if ($.fn.tabularFormset.length === 1) {  // Django < 2.1
			$("#" + config["prefix"] + "-group .tabular.inline-related tbody tr").tabularFormset(config);
		} else {  // Django 2.1+
			$("#" + config["prefix"] + "-group .tabular.inline-related tbody tr").tabularFormset($('this').selector, config);
		}
	});
});