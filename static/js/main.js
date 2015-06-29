"use strict";

$(document).ready(function () {
    ep.init();
});

var ep = ep || {
    init: function() {

        //Initialise Accordion widget
        ep.initAccordion();

        //get Platform info
        $.get("/api/v1/info", function(data){
            $("txt_wlcm_msg").innerHTML = data.welcome_message;
            $("txt_vendor").innerHTML = data.vendor;
            $("txt_sw_version").innerHTML = data.sw_version;
            $("txt_hw_version").innerHTML = data.hw_version;
            $("txt_api_versions").innerHTML = data.supported_api_versions;
        });

        ep.updateModules();

        //Set click handlers for Clear and Export buttons
        $("#btn_clear").on('click', function() {
            $('#log_console').empty();
        });
    },

    generateHeaderContainer: function(id, name) {
        //display slot index
        var result = "<h3 class = 'module_header' id='module_header" + id + "'>" + id + ". ";
        if (name != null) {
            //display module name
            result += name;
        } else {
        result += "Empty slot";
        }

        result = result + "</h3>";
        return result;
    },

    generateControlPanelContainer: function(id, name, used_by) {
        return "<div id='control_panel" + id + "' class = 'disabled control_panel'></div>";
    },

    addHeaderLockButton: function(id, used_by) {
        var btn = $('<a/>', { id: "tgl_lock" + id});

        $('#module_header' + id).append(btn);

        if (used_by != null) {
            btn.addClass("down");
            btn.text("Unlock");
        } else {
            btn.text("Lock");
        }



        btn.click(function() {

            btn.toggleClass("down");
            if (btn.hasClass("down")) {
                //Lock the module
                $.post("/api/v1/module/select?slot=" + id, function(data){
                    writeToConsole("Locking module #" + id + ". Result: " + data + "\n");
                });
                btn.text("Unlock");

            } else {

                $.ajax({
                    url: "/api/v1/module/select?slot=" + id,
                    type: 'DELETE',
                    success: function(data) {
                        ep.writeToConsole("Removing lock from module #" + id + ". Result: " + data + "\n");
                    }
                });
                btn.text("Lock");
                $("#used_by" + id).text(" ");
                $("#used_by" + id).hide();
            }

            //return false to block parent element's click handlers
            return false;
        });
    },

    addCommandSubmitPanel: function(id) {
        var panel = "<div>SCPI command:</div><input id='scpi_command" + id + "' type='text'>";
        panel += "<button id = 'send_scpi" + id + "'>Send</button>";
        $("#control_panel" + id).append(panel);
        $("#control_panel" + id).removeClass('disabled');
        $('#send_scpi' + id).on('click', function() {
            //Send SCPI command to the module
            var command = $('#scpi_command' + id).val();
            ep.writeToConsole("Sending command to module #" + id + ": " + command + "\n");
            $.post("/api/v1/module?slot=" + id, command, function(data){
                ep.writeToConsole("Response from module #" + id + ":\n" + data + "\n");
            });
        });
    },

    initAccordion: function() {
        $('#modules_list').accordion({
            active: false,
            collapsible:true,

            beforeActivate: function(event, ui) {
                // The accordion believes a panel is being opened
                var currHeader;
                var currContent;
                if (ui.newHeader[0]) {
                    currHeader  = ui.newHeader;
                    currContent = currHeader.next('.ui-accordion-content');
                    // The accordion believes a panel is being closed
                } else {
                    currHeader  = ui.oldHeader;
                    currContent = currHeader.next('.ui-accordion-content');
                }

                //Do not process click events if panel is disabled
                if (currContent.hasClass('disabled')) {
                    return false;
                }
            }
        });
    },

    writeToConsole: function (text) {
        $('#log_console').append(text);
    },

    updateModules: function() {
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
                    var header = ep.generateHeaderContainer(i, module[0]);
                    var control_panel = ep.generateControlPanelContainer(i, module[0], module[1]);
                    $('#modules_list').append(header + control_panel);
                    if (i != 0) {
                        //It's not a broadcast module
                        if (module[0] != null) {
                            //Slot is not empty
                            ep.addHeaderLockButton(i, module[1]);
                            ep.addCommandSubmitPanel(i);
                        }
                    } else {
                        //It's a broadcast module
                        ep.addCommandSubmitPanel(i);
                    }
                    $('#modules_list').accordion("refresh");
            }

            $("txt_number_of_slots").innerHTML = data.length;
            $("txt_number_of_modules").innerHTML = num_of_modules;
            $("txt_modules_in_use").innerHTML = used_modules;
        });
    }
};
