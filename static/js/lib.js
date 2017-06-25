/**
 * Created by Administrator on 6/20/2017.
 */

var addBook = function () {
    var title = $("#title").val();
    var genre = $("#genre").val();
    var isbn = $("#isbn").val();
    var author = $("#author").val();
    var year = $("#year").val();
    $.ajax({
        type: "POST",
        url: "/api/books",
        data: JSON.stringify({
            'title': title,
            'genre': genre,
            'isbn': isbn,
            'author': author,
            'year': year
        }),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#book-alert', data['result']);
            } else {
                toggleError('#book-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var updateBook = function () {
    var title = $("#title").val();
    var genre = $("#genre").val();
    var isbn = $("#isbn").val();
    var author = $("#author").val();
    var year = $("#year").val();
    $.ajax({
        type: "PUT",
        url: "/api/books/" + isbn,
        data: JSON.stringify({
            'title': title,
            'genre': genre,
            'author': author,
            'year': year
        }),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#book-alert', data['result']);
            } else {
                toggleError('#book-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var removeBook = function () {
    var isbn = $("#bookIsbnRem").val();
    $.ajax({
        type: "DELETE",
        url: "/api/books/" + isbn,
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#book-alert', data['result']);
            } else {
                toggleError('#book-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var addCopy = function () {
    var isbn = $("#copyIsbn").val();
    $.ajax({
        type: "POST",
        url: "/api/books/" + isbn + "/copies",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#copy-alert', data['result']);
            } else {
                toggleError('#copy-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var removeCopy = function () {
    var isbn = $("#copyIsbn").val();
    var nr = $("#copyNr").val();
    if (!nr) {
        toggleError('#copy-alert', 'Missing copy number');
    }
    $.ajax({
        type: "DELETE",
        url: "/api/books/" + isbn + "/copies/" + nr,
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#copy-alert', data['result']);
            } else {
                toggleError('#copy-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var borrowCopy = function () {
    var isbn = $("#copyIsbnBor").val();
    var number = $("#copyNrBor").val();
    var reader = $("#copyReadBor").val();

    $.ajax({
        type: "PUT",
        url: "/api/books/" + isbn + "/copies/" + number + "/borrow",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({
            'reader': reader
        }),
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#copy-action-alert', data['result']);
            } else {
                toggleError('#copy-action-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var returnCopy = function () {
    var isbn = $("#copyIsbnBor").val();
    var number = $("#copyNrBor").val();
    var reader = $("#copyReadBor").val();

    $.ajax({
        type: "PUT",
        url: "/api/books/" + isbn + "/copies/" + number + "/return",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({
            'reader': reader
        }),
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#copy-action-alert', data['result']);
            } else {
                toggleError('#copy-action-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var extendCopy = function (isbn, number) {
    if (!isbn) isbn = $("#copyIsbnBor").val();
    if (!number) number = $("#copyNrBor").val();

    $.ajax({
        type: "PUT",
        url: "/api/books/" + isbn + "/copies/" + number + "/extend",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (data['result']){
                toggleAlert('#copy-action-alert', data['result']);
            } else {
                toggleError('#copy-action-alert', data['error']);
            }
        },
        failure: function (errMsg) {
            alert(errMsg);
        }
    });
};

var toggleAlert = function (selector, msg) {
    $(selector).attr('class', 'alert alert-dismissible alert-info fade out');
    $(selector).text(msg);
    $(selector).toggleClass('in out');
    window.setTimeout(function() { $(selector).toggleClass('in out'); }, 2000);
    return false; // Keep close.bs.alert event from removing from DOM
};

var toggleError = function (selector, msg) {
    $(selector).attr('class', 'alert alert-dismissible alert-danger fade out');
    $(selector).text(msg);
    $(selector).toggleClass('in out');
    window.setTimeout(function() { $(selector).toggleClass('in out'); }, 2000);
    return false; // Keep close.bs.alert event from removing from DOM
};