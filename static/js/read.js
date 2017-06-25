/**
 * Created by Administrator on 6/20/2017.
 */

var getBorrowedBooks = function () {
    var table = $("#tbl-taken-books");
    table.find("thead th").remove();
    table.find("tbody tr").remove();
    var pageSz = $('#btn-pg-reader').text();
    var pageNr = $('#pg-taken-books .active').text();
    $.ajax({
        type: "GET",
        url: "/api/books/taken",
        data: {
            'pageNr': pageNr,
            'pageSz': pageSz
        },
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            showDataReader(data);
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};