/**
 * Created by hevlhayt@foxmail.com
 * Date: 2016/6/5
 * Time: 19:12
 */

$(function() {
    $('#btn-my-group').click(function() {
        $('#table-my-group').show();
        $('#table-in-group').hide();
        $('#table-rcmd-group').hide();
        $('#box-group').attr('class', 'box box-info').find('h3').text('Manage Groups --- My Created Groups');
    });
    $('#btn-in-group').click(function() {
        $('#table-in-group').show();
        $('#table-my-group').hide();
        $('#table-rcmd-group').hide();
        $('#box-group').attr('class', 'box box-success').find('h3').text('Manage Groups --- My Joined Groups');
    });
    $('#btn-rcmd-group').click(function() {
        $('#table-rcmd-group').show();
        $('#table-my-group').hide();
        $('#table-in-group').hide();
        $('#box-group').attr('class', 'box box-warning').find('h3').text('Manage Groups --- Group Recommendations');
    });

    $('#group-create-modal').on('show.bs.modal', function (e) {
        $(this).find('.modal-dialog').css({
            'margin-top': function () {
                var modalHeight = $('#search').find('.modal-dialog').height();
                return ($(window).height() / 6 - (modalHeight / 2));
            }
        });
    });

    $('input[type="radio"].minimal').iCheck({
        radioClass: 'iradio_flat-green',
    });

    window.msgConfirmed = function(url, type, linkid) {
        $.get(url, function(data){
            if(data == -1) {
                alert("Error");
            }
            else {
                if(type == 1)
                    $('#msg-'+linkid+' > small').attr('class', 'label label-success').text('Confirmed');
                else if(type == 0)
                    $('#msg-'+linkid+' > small').attr('class', 'label label-danger').text('Rejected');
            }
        });
    };

    window.updateMsgPanel = function(page) {
        $.get(msgPanelUrl+'?page='+page, function(data){
            var msg = $('#box-msg');
            msg.find('.box-body').detach();
            msg.find('.box-footer').detach();
            msg.append(data);
        });
    };

    var timeout;
    window.updateInvPanel = function(page, groupname) {
        if(groupname)
            $.get(invPanelUrl+'?page='+page+'&groupname='+groupname, function(data) {
                onUpdateInvSucceess(data);
            });
        else
            $.get(invPanelUrl+'?page='+page, function(data){
                onUpdateInvSucceess(data);
            });
    };

    function onUpdateInvSucceess(data) {
        var inv = $('#box-inv');
        inv.find('.box-body').detach();
        inv.find('.box-footer').detach();
        inv.append(data);

        $('#search-group').bind('input', function () {

            clearTimeout(timeout);
            var text = $(this).val();
            if(text)
                timeout = setTimeout(function () {
                    updateInvPanel(1, text);
                }, 1000);
            else
                timeout = setTimeout(function () {
                    updateInvPanel(1, null);
                }, 1500);
        });
    }

    updateMsgPanel(1);
    updateInvPanel(1, null);

});



