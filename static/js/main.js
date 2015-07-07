"use strict";

$(document).ready(function () {
    ep.init();
    $("#console_clear_btn").click(function(){
        $("#console_log").empty();
    })
});

var ep = window['ep'] || {
    base_url: '',
    slots: 0,
    info: null,
    _username: 'Somebody', // User name from auth, updated at init()
    _username_alias: 'You', // Friendly name to address user in GUI.
                            // It is here for localization purposes
    _api_token: '', // api_token to be used. TODO: figure out how to transfer it
    _empty_slot_str: "Empty slot", // moved out of func for localization purposes
    _broadcast_slot: 0,
    _ws: null, //WebSocket object

    init: function(base_url) {
        // TODO: set global ajax error handler
        if (base_url == null) {
            base_url = window.location.protocol + "//" +window.location.host;
        }

        ep.base_url = base_url;

        setInterval(function(){
            // -1 is for broadcast module
            $("#platform_info_modules").text($("header.active").length-1);
        }, 1000);

        setInterval(function(){
            $("#platform_info_modules_in_use").text(
                $(".module_lock:not(:empty)").length);
        }, 1000);

        //get Platform info
        $.get(ep.base_url + "/api/v1/info?format=json", function(platform_info){
            ep.slots = platform_info.slots;
            $("#platform_info_vendor").text(platform_info['vendor']);
            $("#platform_info_sw_version").text(platform_info['sw_version']);
            $("#platform_info_hw_version").text(platform_info['hw_version']);
            $("#platform_info_slots").text(platform_info['slots']);
            ep.updateModuleList(); // manually update list of modules

            //Init WebSocket session
            ep._ws = new WebSocket("ws://" + window.location.host + "/websocket");
            ep._ws.onmessage = function (event) {
                //Handle a message from WebSocket
                ep.parseWSMessage(event.data);
            }

            // TODO: update ep._username
            // TODO: update ep._api_token
        });
    },

    scpi: function(slot_id, scpi_command, callback) {
        ep.log("Slot "+slot_id+": Request: " + scpi_command);
        $.post(
            ep.base_url + '/api/v1/send_scpi?format=json&slot='+slot_id,
            scpi_command,
            function(scpi_response) {
                if (callback != null) callback(scpi_response);
                ep.log("Slot "+slot_id+": Response: " + scpi_response);
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
            "<span class='module_lock' id='modle_name_"+slot_id+"'></span>"+
            // rest of header
            "</header>" +
            // control panel
            "<section class='control_panel' id='module_control_panel_"+slot_id+
            "'></section>");
        $("#module_header_"+slot_id).click(function() {
            if (!$(this).hasClass("active")) return;
            // if module is being opened, check if is used by somebody

            if (slot_id == ep._broadcast_slot) { // broadcast module is exempt from lock rules
                $(this).toggleClass("open");
                return;
            }
            var lock_container = $(this).find(".module_lock");

            // if module is being closed, just release lock
            if ($(this).hasClass("open")) {
                $.ajax({
                    url: ep.base_url + "/api/v1/lock_module?format=json&slot=" + slot_id,
                    type: 'DELETE',
                });
                lock_container.empty();
                $(this).toggleClass("open", false);
                return;
            }

            // container is being opened
            var locked_by = lock_container.text();
            if (locked_by && locked_by != ep._username &&
                locked_by != ep._username_alias &&
                confirm("This module is used by " + locked_by + ". Do you " +
                        "want to force unlock it?")) {
                // used by somebody - try force unlock
                if ($.ajax({type: 'DELETE', async: false,
                        url: ep.base_url + "/api/v1/lock_module?format=json&slot=" + slot_id
                        }).responseText != "OK") {
                    alert("Failed to unlock module. Please try again");
                    return;
                }
                // mark module as used
                if ($.ajax({ type: 'POST', async: false,
                        url: ep.base_url + "/api/v1/lock_module?format=json&slot=" + slot_id
                        }).responseText != "OK") {
                    alert("Failed to acquire module lock. Please unlock and try again");
                    return;
                }
            }
            lock_container.text(ep._username_alias);
            $(this).toggleClass("open", true);
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

                ep._updateModuleUI(slot_id, module_name);

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
        header.removeClass("open");
        // update module name in header
        $("#module_name_" + slot_id).text(module_name || ep._empty_slot_str);
        // manually update lock status
        if (module_name == null || slot_id==ep._broadcast_slot) {
            // Broadcast pseudo module
            ep._markUsedBy(slot_id, null);
        } else {
            ep._updateModuleLockStatus(slot_id, module_name);
        }

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
        var lock_container = $("#module_header_"+slot_id).find(".module_lock");
        if (username) {
            lock_container.text(ep._username_alias);
        } else {
            //Module is not locked by anyone
            lock_container.empty();
        }
    },

    parseWSMessage: function (message) {
        console.log("Message from ws: " + message);
        var json = JSON.parse(message);
        switch (json.msg_type) {
            case 'MODULE_UPDATE':
                //Request to update Module info has been received
                ep._updateModuleUI(json.slot, json.module_name);
                break;
        }
    },

    log: function(message) {
        // HTML is welcome
        $("#console_log").append(message+"<br />");
    }
};
