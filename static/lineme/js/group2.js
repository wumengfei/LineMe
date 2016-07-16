/**
 * Created by hevlhayt@foxmail.com
 * Date: 2016/7/15
 * Time: 17:40
 */

$(function() {

    $('.modal').on('show.bs.modal', function (e) {
        $(this).find('.modal-dialog').css({
            'margin-top': function () {
                var modalHeight = $('#member-join-modal').find('.modal-dialog').height();
                return ($(window).height() / 6 - (modalHeight / 2));
            }
        });
    });

    $('input[type="radio"].minimal').iCheck({
        radioClass: 'iradio_flat-green'
    });

    function joinGroup() {

        $.get(joinUrl, function(result) {

            switch (result) {

                case '0':
                    window.location.replace(egoUrl);
                    break;
                case '-1':
                    if (identifier == 0) {
                        var $modal = $('#modal-content-wrong');
                        $modal.find('.modal-title').text('Identifier');
                        $modal.find('.modal-footer button').val('Follow');
                        $modal.find('input').attr('placeholder', '');
                        $modal.show();
                        $('#modal-content-notin').hide();

                        $('#member-join-modal').modal('show');
                    }
                    else {
                        $('#modal-content-wrong').show();
                        $('#modal-content-notin').hide();

                        $('#member-join-modal').modal('show');
                    }
                    break;
                case '-2':
                    $('#modal-content-wrong').hide();
                    $('#modal-content-notin').show();

                    $('#member-join-modal').modal('show');
                    break;
                case '-4':
                    alert('Server Internal Error');
                    break;
                default :
                    break;
            }
        });
    }

    $('#follow').click(function() {
        joinGroup();
    });

});


