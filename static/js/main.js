"use strict";

$(document).ready(function () {
    ep.init();
});

var ep = window['ep'] || {
    base_url: '',
    slots: 0,
    _username: 'Somebody', // User name from auth, updated at init()
    _api_token: '', // api_token to be used. TODO: figure out how to transfer it
    _empty_slot_str: "Empty slot", // moved out of func for localization purposes
    _broadcast_slot: 0,

    init: function(base_url) {
        // set global ajax error handler
        /*
        $(document).ajaxError(function(event, jqxhr, settings, error) {
           alert("Something went wrong, and we're working hard to fix " +
               "the problem (not really). Meanwhile, could you please tell "+
               "your technician that you've got an error: \n" +
               "API call to url "+settings.url+" failed with error: " + error
           )
        }); */
        if (base_url == null) {
            base_url = window.location.protocol + "//" +window.location.host;
        }
        ep.base_url = base_url;

        //get Platform info
        $.get(ep.base_url + "/api/v1/info?format=json", function(platform_info){
            ep.slots = platform_info.slots;
            ep.updateModuleList(); // manually update list of modules

            // TODO: set websocket listener to update modules
            // in websocket we expect slot id and module name

            // TODO: update ep._username
            // TODO: update ep._api_token
        });
    },

    scpi: function(slot_id, scpi_command, callback) {
        $.post(
            ep.base_url + '/api/v1/send_scpi?format=json&slot='+slot_id,
            scpi_command,
            function(scpi_response) {
                if (callback != null) callback(scpi_response);
                ep.log(slot_id, scpi_command, scpi_response);
            }
        );
    },

    _add_module: function(container, slot_id, module_name) {
        /* the only reason not to make this function inline is a use case with
        dynamic extension of ports. If module is connected into non-standard
        port, e.g. directly to free USB slot, or platform is not configured
        correctly, new slot will be dynamically created above number specified
        in platform info slots.
        In future, we might consider switching to a normal template engine like
        Mustache */
        container.append("<header id='module_header_"+slot_id+"'>"+slot_id+".&nbsp;" +
            // module name
            "<span class='module_name' id='module_name_"+slot_id+"'>"+
            (module_name||ep._empty_slot_str)+"</span>" +
            // module lock
            "<span class='module_lock' id='modle_name_"+slot_id+"'>You</span>"+
            // rest of header
            "</header>" +
            // control panel
            "<section class='control_panel' id='module_control_panel_"+slot_id+
            "'></section>");
        $("#module_header_"+slot_id).click(function(){
            if (!$(this).hasClass("active")) return;
            $(this).toggleClass("open");
        });
    },

    updateModuleList: function() {  //manually update full list of modules
        // create containers for modules by number of slots in this platform
        var module_list_container = $('#modules_list');
        module_list_container.empty();
        // ep.slots + 1 because of Broadcast module in slot 0
        for (var i=0; i<ep.slots+1; i++)
            ep._add_module(module_list_container, i, ep._empty_slot_str);

        // get list of modules and update created containers
        $.get(ep.base_url+"/api/v1/modules_list?format=json", function(modules){
            modules.forEach(function(module_name, slot_id) {
                if (slot_id > ep.slots) {
                    /* module plugged through standalone adapter or platform
                    * ports are not configured - add new slot dynamically */
                    ep._add_module(module_list_container, slot_id, ep._empty_slot_str);
                }
                // update module name in header
                $("#module_name_" + slot_id).text(module_name || ep._empty_slot_str);

                ep._updateModuleUI(slot_id, module_name);

                // manually update lock status
                if (module_name == null || slot_id==ep._broadcast_slot) {
                    // Broadcast pseudo module
                    ep._markUsedBy(slot_id, null);
                }
                else {
                    ep._updateModuleLockStatus(slot_id, module_name);
                }

                // TODO: set websocket listener to monitor lock status

            });
        });
    },

    _updateModuleUI: function(slot_id, module_name) {
        /* TODO: replace with next sibling selector (less chance to be screwed
        up with custom themes */
        var control_panel = $("#module_control_panel_"+slot_id);
        var header = $("#module_header_"+slot_id);

        // DISABLE MODULE
        // collapse module control panel
        control_panel.empty();
        // mark module inactive
        header.removeClass("active");

        if (module_name == null) return;

        // FROM THIS POINT ON, IT IS A REAL MODULE
        // get module webUI based on config
        var widgets_script_url = ep.base_url +
            '/api/v1/module_ui_controls?format=json&slot=' +
            slot_id + '&container=%23module_control_panel_'+slot_id;
        $.getScript(widgets_script_url).done(function(){
            // mark module active
            header.addClass("active");
        });
    },

    _updateModuleLockStatus: function(slot_id) {
        if (slot_id == ep._broadcast_slot) {
            // TODO: log warning
        }
        else {
            $.get(ep.base_url+"/api/v1/lock_module?format=json&slot=" + slot_id,
                function (username) {
                    ep._markUsedBy(slot_id, username)
                });
        }
    },

    _markUsedBy: function(slot_id, username) {
        // TODO: add GUI
    },

    log: function(slot_id, scpi_command, scpi_response) {
        if (scpi_response == null) { // log(scpi_command, scpi_response)
            scpi_response = scpi_command;
            scpi_command = slot_id;
            slot_id = null;
            if (scpi_response == null) { // log(scpi_response)
                scpi_response = scpi_command;
                scpi_command = null;
            }
        }
        alert(scpi_response);
    }
};
