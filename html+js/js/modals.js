function shortenId(id_text) {
    if (id_text.length < 10) return id_text;
    return id_text.substr(0, 3) + '...' + id_text.substr(id_text.length - 3);
}

function mr_getSourceHTML(data) {
    var s = data.s.a;
    var avatar = s.picture_url ? s.picture_url : '/img/avatar.png';
    return "<a href='" + s.url + "' target='_blank'><img src='" + avatar + "'></img>&nbsp;" + s.name + "&nbsp;<abbr class='label label-default hidden-mobile' title='" + s.id + "'>" + shortenId(s.id) + "</abbr></a>"

}
function mr_getTargetHTML(data) {
    var a = data.a;
    var avatar = a.picture_url ? a.picture_url : '/img/avatar.png';
    return "<a href='" + a.url + "' target='_blank'><img src='" + avatar + "'></img>&nbsp;" + a.name + "&nbsp;<abbr class='label label-default hidden-mobile' title='" + a.id + "'>" + shortenId(a.id) + "</abbr></a>";
}

function mr_getLinkHTML(data) {
    return "<div class='input-group friends-list'>" + mr_getSourceHTML(data) + " <i> to </i> <b><span style='text-transform: capitalize;'>" + data.p + "</span> / </b>" + mr_getTargetHTML(data) + "</div>";
}

function LinksDataTable(name, onSettings, onSync) {
    var self = this;
    var lastIdx = null;

    self.checked_list = [];

    /* DataTable  */
    var responsiveHelper_datatable_fixed_column = undefined;
    var breakpointDefinition = {
        tablet: 1024,
        phone: 480
    };
    self.otable = $(name).DataTable({
        "sDom": "t<'dt-toolbar-footer'<'col-sm-6 col-xs-12 hidden-xs'i><'col-xs-12 col-sm-6'p>>",
        "bLengthChange": false,
        "iDisplayLength": 50,
        "preDrawCallback": function () {
            // Initialize the responsive datatables helper once.
            if (!responsiveHelper_datatable_fixed_column) {
                responsiveHelper_datatable_fixed_column = new ResponsiveDatatablesHelper($(name), breakpointDefinition);
            }
        },
        "rowCallback": function (nRow, data, index) {
            responsiveHelper_datatable_fixed_column.createExpandIcon(nRow);
            $(nRow).removeClass('highlight highlight-first');
            var idx = self.checked_list.indexOf(data.li.uid);
            if (idx == 0) {
                $(nRow).addClass('highlight-first');
            } else if (idx > 0) {
                $(nRow).addClass('highlight');
            }
        },
        "drawCallback": function (oSettings) {
            responsiveHelper_datatable_fixed_column.respond();
        },
        "columnDefs": [
            {
                "targets": 0,
                "data": null,
                "searchable": false,
                "orderable": false,
                "defaultContent": '<div class="checkbox"><label><input type="checkbox"></label></div>',
                "data": function (sData, kind) {
                    if (kind == 'display') {
                        return '<div class="checkbox"><label><input type="checkbox" id="' + sData.li.uid + 'c"' + (self.checked_list.indexOf(sData.li.uid) >= 0 ? " checked" : "") + '></label></div>';
                    }
                    return null;
                },
            },
            {
                "targets": 1,
                "data": "p",
            },
            {
                "targets": 2,
                "data": function (oData, kind) {
                    var a = oData.a;
                    if (kind == 'display') {
                        return "<div class='input-group friends-list'>" + mr_getTargetHTML(oData) + "</div>";
                    } else {
                        return a.name + ' (' + a.id + ')';
                    }
                }
            },
            {
                "targets": 3,
                "data": function (oData, kind) {
                    var a = oData.s.a;
                    if (kind == 'display') {
                        return "<div class='input-group friends-list'>" + mr_getSourceHTML(oData) + "</div>";
                    }
                    else {
                        return a.name + ' (' + a.id + ')'; 
                    }
                },               
            },
            {
                "targets": 4,
                "data": function (sData, kind) {
                    if (kind == 'display') {
                        return "<button class='btn btn-default' id='" + sData.li.uid + "s'><i class='fa fa-fw fa-sliders'></i></button>";
                    } 
                    return null;                   
                },
                "searchable": false,
                "orderable": false,
            },
        ],
        "order": [[1, 'asc'], [2, 'asc'], [3, 'asc']],
    });

    // Apply the filter
    $(name + ' thead th input[type=text]').on('keyup change', function () {
        self.otable
            .column($(this).parent().index() + ':visible')
            .search(this.value)
            .draw();
    });

    // link button actions
    $(name + ' tbody').on('click', 'button', function (a, b) {
        var data = self.otable.row($(this).closest('tr')).data();
        onSettings(data);
    });

    // link checkbox
    $(name + ' tbody').on('click', 'td:not(:has(button))', function (a, b) {
        var row = self.otable.row($(this).closest('tr'));
        var data = row.data();
        var idx = self.checked_list.indexOf(data.li.uid);
        if (idx == 0) {
            self.checked_list.splice(idx, 1);
        }
        else if (idx > 0) {
            self.checked_list.splice(idx, 1);
            self.checked_list.unshift(data.li.uid);
        }
        else {
            self.checked_list.push(data.li.uid);
        }
        row.invalidate().draw(false);
    });

    self.getChecked = function () {
        var rows = self.otable.rows(function (idx, data, node) {
            return self.checked_list.indexOf(data.li.uid) > 0 ? true : false;
        }, { search: 'applied' });
		
		var ref_row = self.otable.rows(function (idx, data, node) {
            return self.checked_list.indexOf(data.li.uid) == 0 ? true : false;
        }, { search: 'applied' });
		
		// zero element must be first		
        return ref_row.data().toArray().concat(rows.data().toArray());
    };

    self.checkedCount = function () {
        return self.checked_list.length;
    };

    self.toggleSelectAll = function () {
        if (self.checked_list.length >= self.otable.rows({ search: 'applied' }).data().length) {
            self.checked_list.length = 0;
        } else {
            $.each(self.otable.rows({ search: 'applied' }).data(), function (i, row) {
                var idx = self.checked_list.indexOf(row.li.uid);
                if (idx >= 0) {
                    self.checked_list.splice(idx, 1);
                } else {
                    self.checked_list.push(row.li.uid);
                }
            });
        }
        self.otable.rows().invalidate().draw();
    }

    self.selectAll = function (clear) {
        if (clear || self.checked_list.length >= self.otable.rows({ search: 'applied' }).data().length) {
            self.checked_list.length = 0;
        } else {
            $.each(self.otable.rows({ search: 'applied' }).data(), function (i, row) {
                if (self.checked_list.indexOf(row.li.uid) < 0)
                    self.checked_list.push(row.li.uid);
            });
        }
        self.otable.rows().invalidate().draw();
    }

    self.getLinkHTML = function (uid) {
        var data = $.grep(self.otable.data(), function (row) {
            return row.li.uid == uid;
        });
        return data && data.length > 0 ? mr_getLinkHTML(data[0]) : "";
    }

    self.clear = function () {
        self.otable.clear();
        self.checked_list.length = 0;
    }
}