$(document).ready(function (){
    //get Platform info
    $.get("/api/v1/info", function(data){
	document.getElementById("txt_wlcm_msg").innerHTML = data['welcome_message'];
	document.getElementById("txt_vendor").innerHTML = data['vendor'];
	document.getElementById("txt_sw_version").innerHTML = data['sw_version'];
	document.getElementById("txt_hw_version").innerHTML = data['hw_version'];
	document.getElementById("txt_api_versions").innerHTML = data['supported_api_versions'];
    })

    //get list of modules and their statuses
    $.get("/api/v1/modules_list", function(data){
	var num_of_modules = 0;
	var used_modules = 0;

    for (var i=0; i < data.length; i++) {
	        var module = data[i];
	        if (module[0] != null) {
		        num_of_modules = num_of_modules + 1;
		        if (module[1] != null) {
		            used_modules = used_modules + 1;
		        }

	        }
	        var header = generateHeaderContainer(i, module[0], module[1]);
            var control_panel = generateControlPanelContainer(i, module[0], module[1]);
    	    $('#modules_list').append(header + control_panel);
    	    //if (i != 0 && module[0] != null) {
    	        addHeaderLockButton(i, module[1]);
    	        addCommandSubmitPanel(i); //Temporary
    	    //}
            $('#modules_list').accordion("refresh");
    }

	document.getElementById("txt_number_of_slots").innerHTML = data.length;
	document.getElementById("txt_number_of_modules").innerHTML = num_of_modules;
	document.getElementById("txt_modules_in_use").innerHTML = used_modules;
    })
})
function generateHeaderContainer(id, name, used_by) {
    //display slot index
    var result = "<h3 id='module_header" + id + "'>" + id + ". ";
    if (name != null) {
        //display module name
        result += name;

	//if it's not a broadcast module
    	if (id != 0) {

	        if (used_by !=null) {
	            //add id of user the module is locked by
	            result = result + " Used by: " + used_by;
	        }
        }
    } else {
	result += "Empty slot";
    }

    result = result + "</h3>";
    return result;
}

function generateControlPanelContainer(id, name, used_by) {
    return "<div id='control_panel" + id + "'></div>";
}

function addHeaderLockButton(id, is_locked) {
    var btn = $('<a/>', { id: "tgl_lock" + id});
    btn.text("Lock");
    //Lock the module
    btn.click(function() {

        $(this).toggleClass("down");
        if ($(this).hasClass("down")) {
            $(this).text('Unlock');
        } else {
            $(this).text('Lock');
        }

        //return false to block parent element's click handlers
        return false;
    })
    if (is_locked != null) {
        $(this).trigger( "click" );
    }
    $('#module_header' + id).append(btn);
}

function addCommandSubmitPanel(id) {
    var panel = "<div>SCPI command:</div><input id='scpi_command" + id + "' type='text'>";
    panel += "<button id = 'send_scpi" + id + "'>Send</button>";
    $("#control_panel" + id).append(panel);
    $('#send_scpi' + id).on('click', function() {
        //Send SCPI command to the module
        var command = $('#scpi_command' + id).val();
        console.log("Command: " + command); //TODO delete
        $.post("/api/v1/module?slot=" + id, {command}, function(data){
            console.log("Response: " + data); //TODO delete
            $('#log_console').append("Response from module #" + id + ": " + data + "\n");
        });
    });
}

$(function() {
    $('#modules_list').accordion({
    collapsible:true,

    beforeActivate: function(event, ui) {
         // The accordion believes a panel is being opened
        if (ui.newHeader[0]) {
            var currHeader  = ui.newHeader;
            var currContent = currHeader.next('.ui-accordion-content');
         // The accordion believes a panel is being closed
        } else {
            var currHeader  = ui.oldHeader;
            var currContent = currHeader.next('.ui-accordion-content');
        }
         // Since we've changed the default behavior, this detects the actual status
        var isPanelSelected = currHeader.attr('aria-selected') == 'true';

         // Toggle the panel's header
        currHeader.toggleClass('ui-corner-all',isPanelSelected).toggleClass('accordion-header-active ui-state-active ui-corner-top',!isPanelSelected).attr('aria-selected',((!isPanelSelected).toString()));

        // Toggle the panel's icon
        currHeader.children('.ui-icon').toggleClass('ui-icon-triangle-1-e',isPanelSelected).toggleClass('ui-icon-triangle-1-s',!isPanelSelected);

         // Toggle the panel's content
        currContent.toggleClass('accordion-content-active',!isPanelSelected)
        if (isPanelSelected) { currContent.slideUp(); }  else { currContent.slideDown(); }

        return false; // Cancel the default action
    }
    });
  });