/**
 * Created by Administrator on 6/24/2017.
 */

var getAllBooks = function (search, pageSz, pageNr) {

    if (pageSz == null) {
        pageSz = $('#btn-pg-main').text();
    }
    if (pageNr == null) {
        pageNr = 1;//$('#pg-main-books .active').text();
    }
    $.ajax({
        type: "GET",
        url: "/api/books",
        data: {
            'search': search,
            'pageSz': pageSz,
            'pageNr': pageNr
        },
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            showDataMain(data);
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var showDataMain = function (data) {
    $('#pg-main-books').attr('class', 'pagination');
    removeMainTable();
    var table = $("#tbl-available-books");
    var head = $('<tr>')
        .append($('<th>').text('Title'))
        .append($('<th>').text('Genre'))
        .append($('<th>').text('Year'))
        .append($('<th>').text('Author'))
        .append($('<th>').text('Available'));
    table.find('thead').append(head);
    var result = data['result'];
    if (result.length > 0) {
        for (var book in result) {
            var row = $('<tr>')
                .append($('<td>').text(result[book].title))
                .append($('<td>').text(result[book].genre))
                .append($('<td>').text(result[book].year))
                .append($('<td>').text(result[book].author))
                .append($('<td>').text(result[book].count));
            table.find('tbody').append(row);
        }
    } else {
        table.find('tbody').append($('<tr>')
            .append($('<td>').text('No result')));
    }
};

var showDataReader = function (data) {
    $('#pg-taken-books').attr('class', 'pagination');
    removeBorrowedTable();
    var table = $("#tbl-taken-books");
    var result = data['result'];
    var today = new Date();
    var head = $('<tr>')
        .append($('<th>').text('Title'))
        .append($('<th>').text('Genre'))
        .append($('<th>').text('Year'))
        .append($('<th>').text('Author'))
        .append($('<th>').text('Taken on'))
        .append($('<th>').text('Return date'));
    table.find('thead').append(head);
    if (result.length > 0) {
        for (var book in result) {
            var return_date = new Date(result[book].return);
            var isExpired = return_date < today;
            var row = $('<tr>')
                .attr({'class': isExpired ? 'warning' : ''})
                .append($('<td>').text(result[book].title))
                .append($('<td>').text(result[book].genre))
                .append($('<td>').text(result[book].year))
                .append($('<td>').text(result[book].author))
                .append($('<td>').text(result[book].borrow))
                .append($('<td>').text(result[book].return))
                .append($('<input>')
                    .attr({'type': 'button'})
                    .attr({'class': isExpired ? 'btn btn-success' : 'btn btn-success disabled'})
                    .on('click', function () {
                        extendCopy(result[book].isbn, result[book].number)
                    })
                    .val('Extend'));
            table.find('tbody').append(row);
        }
    } else {
        table.find('tbody').append($('<tr>')
            .append($('<td>').text('No result')));
    }
};

var removeMainTable = function () {
    var table = $("#tbl-available-books");
    table.find("thead th").remove();
    table.find("tbody tr").remove();
};

var removeBorrowedTable = function () {
    var table = $("#tbl-taken-books");
    table.find("thead th").remove();
    table.find("tbody tr").remove();
};

var hideMainPagination = function () {
    $('#pg-main-books').attr('class', 'pagination hidden');
    $('#pg-main-left').attr('class', 'disabled');
    $('#pg-main-right').attr('class', '');
    $('#page-number-main a').text(1);
};

$(document).ready(function () {
    $('#ul-page-size-main li').on('click', function () {
        $('#btn-pg-main').text($(this).text());
    });

    $('#pg-main-right').on('click', function () {
        if ($(this).hasClass('disabled')) {
            return false;
        }
        $('#pg-main-left').attr('class', '');
        var currentPage = parseInt($('#page-number-main').text());
        var pageSize = parseInt($('#btn-pg-main').text());
        var search = $('#txt-search').val();
        $.get('/api/books', {search: search, pageNr: currentPage + 1, pageSz: pageSize}, function (response) {
            if (response != null && response['result'].length > 0) {
                currentPage++;
                $('#pg-main-left').attr('class', '');
                var rowCount = response['result'].length;

                $('#page-number-main a').text(currentPage);
                showDataMain(response);
            } else {
                $('#pg-main-right').attr('class', 'disabled');
            }
        });
    });

    $('#pg-main-left').on('click', function () {
        if ($(this).hasClass('disabled')) {
            return false;
        }
        $('#pg-main-right').attr('class', '');
        var currentPage = parseInt($('#page-number-main').text());
        if (currentPage < 2) {
            $('#pg-main-left').attr('class', 'disabled');
            return false;
        }
        var pageSize = parseInt($('#btn-pg-main').text());
        var search = $('#txt-search').val();
        $.get('/api/books', {search: search, pageNr: currentPage - 1, pageSz: pageSize}, function (response) {
            if (response != null && response['result'].length > 0) {
                currentPage--;
                $('#pg-main-right').attr('class', '');
                var rowCount = response['result'].length;

                $('#page-number-main a').text(currentPage);
                showDataMain(response);
            } else {
                $('#pg-main-left').attr('class', 'disabled');
            }
        });
    });

    $('#btn-pg-main-items').on('click', function () {
        removeMainTable();
        hideMainPagination();
    });

    $('#show-books').on('click', function () {
        $('#pg-main-books').attr('class', 'pagination');
        getAllBooks();
    });

    /******************* READER ********************/
    // set page number
    $('#ul-page-size-reader li').on('click', function () {
        $('#btn-pg-reader').text($(this).text());
    });

    $('#pg-taken-right').on('click', function () {
        if ($(this).hasClass('disabled')) {
            return false;
        }
        $('#pg-taken-left').attr('class', '');
        var currentPage = parseInt($('#page-number-reader').text());
        var pageSize = parseInt($('#btn-pg-reader').text());
        $.get('/api/books/taken', {pageNr: currentPage + 1, pageSz: pageSize}, function (response) {
            if (response != null && response['result'].length > 0) {
                currentPage++;
                $('#pg-taken-left').attr('class', '');
                var rowCount = response['result'].length;

                $('#page-number-reader a').text(currentPage);
                showDataReader(response);
            } else {
                $('#pg-taken-right').attr('class', 'disabled');
            }
        });
    });

    $('#pg-taken-left').on('click', function () {
        if ($(this).hasClass('disabled')) {
            return false;
        }
        $('#pg-taken-right').attr('class', '');
        var currentPage = parseInt($('#page-number-reader').text());
        if (currentPage < 2) {
            $('#pg-taken-left').attr('class', 'disabled');
            return false;
        }
        var pageSize = parseInt($('#btn-pg-reader').text());
        $.get('/api/books/taken', {pageNr: currentPage - 1, pageSz: pageSize}, function (response) {
            if (response != null && response['result'].length > 0) {
                currentPage--;
                $('#pg-taken-right').attr('class', '');
                var rowCount = response['result'].length;

                $('#page-number-reader a').text(currentPage);
                showDataReader(response);
            } else {
                $('#pg-taken-left').attr('class', 'disabled');
            }
        });
    });
    var hideReaderPagination = function () {
        $('#pg-taken-books').attr('class', 'pagination hidden');
        $('#pg-taken-left').attr('class', 'disabled');
        $('#pg-taken-right').attr('class', '');
        $('#page-number-reader a').text(1);
    };
    $('#btn-pg-reader-items').on('click', function () {
        removeBorrowedTable();
        hideReaderPagination();
    });

    $('#show-books-reader').on('click', function () {
        $('#pg-main-books').attr('class', 'pagination');
        getBorrowedBooks();
    });
});
