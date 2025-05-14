/**
 *
 * Copyright 2025, Institute for Systems Biology
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

$(document).ready(function () {
    let typingTimer;
    const doneTypingInterval = 500; // Time in ms (0.5 seconds)

    let query_param_url = set_filters();
    let table = $('#bqmeta').DataTable({
        dom: 'lfBrtip',
        ajax: {
            method: 'GET',
            url: '/search_api' + query_param_url,
            dataSrc: '',
        },
        buttons: [
            {
                className:'reset-btn',
                text: '<i class="fa-solid fa-rotate-left"></i> Reset All Filters',
            },
            {
                collectionTitle: 'Select Columns to Display</span>',
                extend: 'colvis',
                text: '<i class="fa-solid fa-sliders"></i> Columns <span class="caret"></span>',
                columns: '.colvis-toggle',
                postfixButtons: [
                    {
                        extend: 'colvisRestore',
                        text: '<i class="fa-solid fa-rotate-left"></i> Restore'
                    }
                ]
            },
            {
                extend: 'csvHtml5',
                text: '<i class="fa-solid fa-download"></i> CSV Download',
                title: 'bq-metadata',
                exportOptions: {
                    columns: ':not(".no-export")'
                }
            }
        ],
        columns: [
            {
                "className": 'no-export',
                "orderable": false,
                "data": null,
                "defaultContent": '',
                'render': function (data, type) {
                    if (type === 'display') {
                        return '<a class="px-0 details-control rounded badge" title="View Table Details"><i class="plus-control px-1 fa-solid fa-plus"></i><i class="minus-control px-1 fa-solid fa-minus" style="display: none;"></i></a>'
                    }
                }
            },
            {
                'name': 'friendlyName',
                'data': function (data) {
                    return (data.friendlyName ? data.friendlyName : (data.tableReference.datasetId + '-' + data.tableReference.tableId)).toUpperCase();
                },
                'className': 'label-filter colvis-toggle'
            },
            {
                'data': function (row) {
                    return {
                        id: row.id.split(/[.:]/).join('/'),
                        access: row.labels ? (row.labels.access ? row.labels.access : '') : '',
                        link: format_bq_gcp_console_link(row.tableReference)
                    };
                },
                'render': function (data, type) {
                    if (type === 'display') {
                        let preview_btn_html;
                        let gcp_btn_html;
                        if (data.access && data.access === 'controlled') {
                            preview_btn_html = '<div title="Unavailable for Controlled Access Data"><div class="tbl-preview disabled"></div></div>';
                            // return '<div title="Unavailable for Controlled Access Data"><div class="tbl-preview disabled"></div></div>';

                            // if (data.access && data.access === 'open') {
                            //     if(user_is_authenticated){
                            //         if(user_is_ca_authorized){
                            //             return '<div class="tbl-preview" title="Preview Table"><i class="preview-loading fa fa-circle-o-notch fa-spin" style="display: none; color:#19424e;" aria-hidden="true"></i></div>';
                            //         }
                            //         else{
                            //             return '<div title="You do not have access to this table."><div class="tbl-preview disabled"></div></div>';
                            //         }
                            //     }
                            //     else{
                            //         return '<div title="Please sign in to view"><div class="tbl-preview disabled"></div></div>';
                            //     }
                        } else {
                            preview_btn_html = '<a class="stacked-badge-btn tbl-preview badge rounded-pill bqmeta-outline-badge" title="Open in Google Cloud Console"><i class="preview-loading fa-solid fa-circle-notch fa-spin" style="display: none;" aria-hidden="true"></i><i class="preview-icon fa-solid fa-magnifying-glass"></i> PREVIEW</a>';
                        }
                        gcp_btn_html = '<a class="stacked-badge-btn open-gcp-btn badge rounded-pill bqmeta-outline-badge" data-gcpurl="'
                            + data.link
                            + '" title="Open in Google Cloud Console"><i class="fa-solid fa-cloud"></i> OPEN BQ</a>'
                        return preview_btn_html + '</br>'+ gcp_btn_html;
                    } else {
                        return data;
                    }
                },
                'className': 'no-export',
                'searchable': false,
                'orderable': false
            },
            {
                'className': 'colvis-toggle',
                'name': 'version_type',
                'data': function (data) {
                    let table_version = filtered_label_data(data.labels, 'version');
                    return {
                        'table_version': table_version ? table_version.replaceAll('_','.'): null,
                        'releases': data.versions,
                        'type':  (data.id.endsWith('_current') ? 'Always Newest' : 'Stable')
                    }
                },
                'render': function (data) {
                    let html_version = '';
                    if (data.table_version){
                        html_version = data.table_version;
                        let num_vers = data.releases ? Object.keys(data.releases).length:0;
                        let ver_cls = num_vers ? 'view-versions me-2': 'me-4';
                        let btn_title = num_vers ? 'View Version History':'';
                        html_version = '<span title="'+btn_title+'" class="'+ver_cls+'">'+html_version+'</span>';
                        html_version += '</br>('+data.type+')';
                    }

                    return html_version;
                },
                'searchable': true
            },
            {
                'name': 'projectId',
                'data': 'tableReference.projectId',
                'visible': false,
                'className': 'colvis-toggle'
            },
            {
                'name': 'datasetId',
                'data': 'tableReference.datasetId',
                'visible': false,
                'className': 'colvis-toggle',
            },
            {
                'name': 'tableId',
                'data': 'tableReference.tableId',
                'render': function (data, type) {
                    return type === 'display' ?
                        '<div class="nowrap-ellipsis">' + data + '</div>' :
                        data;
                },
                'width': '100px',
                'className': 'custom-width-100 colvis-toggle',
                'visible': false
            },
            {
                'name': 'FullId',
                'data': function (data) {
                    return formatFullId(data.tableReference, true);
                },
                'visible': false
            },
            {
                'name': 'program',
                'data': function (data) {
                    return filtered_label_data(data.labels, 'program');
                },
                'render': function (data, type) {
                    return format_label_display(data, type);
                },
                'className': 'label-filter colvis-toggle'
            },
            {
                'name': 'category',
                'data': function (data) {
                    return filtered_label_data(data.labels, 'category');
                },
                'render': function (data, type) {
                    return format_label_display(data, type);
                },
                'className': 'label-filter colvis-toggle'
            },
            {
                'name': 'reference_genome',
                'data': function (data) {
                    return filtered_label_data(data.labels, 'reference_genome');

                },
                'visible': false
            },
            {
                'name': 'source',
                'data': function (data) {
                    return filtered_label_data(data.labels, 'source');
                },
                'render': function (data, type) {
                    return format_label_display(data, type);
                },
                'className': 'label-filter colvis-toggle'
            },
            {
                'name': 'data_type',
                'data': function (data) {
                    return filtered_label_data(data.labels, 'data_type');
                },
                'render': function (data, type) {
                    return format_label_display(data, type);
                },
                'className': 'label-filter colvis-toggle'
            },
            {
                'name': 'experimental_strategy',
                'data': function (data) {
                    return filtered_label_data(data.labels, 'experimental_strategy');
                },
                'render': function (data, type) {
                    return format_label_display(data, type);
                },
                'className': 'label-filter colvis-toggle',
                'visible': false
            },
            {
                'name': 'status',
                'data': function (data) {
                    return (data.labels && data.labels.status) ? data.labels.status : null;
                },
                'render': function (data, type) {
                    return format_label_display(data, type);
                },
                'className': 'label-filter colvis-toggle'
            },
            {
                'name': 'numRows',
                'data': function (data) {
                    return data.numRows;
                },
                'className': 'text-end colvis-toggle',
                'render': function (data, type) {
                    if (type === 'display') {
                        return $.fn.dataTable.render.number(',', '.').display(data);
                    } else return data;
                }

            },
            {
                'name': 'createdDate',
                'data': 'creationTime',
                'className': 'text-end colvis-toggle',
                'render': function (data, type) {
                    if (type === 'display') {
                        let date = new Date(parseInt(data));
                        let month = date.getMonth() + 1;
                        return month + "/" + date.getDate() + "/" + date.getFullYear();
                    } else {
                        return data;
                    }
                },
                'searchable': false
            },
            {
                'className': 'useful-join-detail colvis-toggle',
                'name': 'usefulJoins',
                'data': function (data) {
                    return data.usefulJoins;
                    // return [
                    //     {
                    //         "title": "Clinical and Biospecimen Data",
                    //         "description": "This query displays CCLE clinical and biospecimen records.",
                    //         "tables": [
                    //             "isb-cgc-bq:CCLE.clinical_current"
                    //         ],
                    //         "sql": "#Retrieve all CCLE clinical cases. Using the LEFT JOIN, if biospecimen records exist for them, get them also.\nSELECT clin.case_barcode, clin.case_gdc_id, clin.project_short_name, clin.site_primary,\n       biospec.sample_barcode, biospec.sample_gdc_id  \nFROM `isb-cgc-bq.CCLE.clinical_current` clin\nLEFT JOIN `isb-cgc-bq.CCLE.biospecimen_current` biospec\nON clin.case_barcode = biospec.case_barcode\nORDER BY clin.case_barcode, biospec.sample_barcode",
                    //         "condition": "clin.case_barcode = biospec.case_barcode"
                    //     },
                    //     {
                    //         "title": "Counting Samples per Case",
                    //         "description": "This query finds all cases having more than one sample.",
                    //         "tables": [
                    //             "isb-cgc-bq:CCLE.clinical_current"
                    //         ],
                    //         "sql": "#Find all cases having more than one sample\nSELECT clin.case_barcode, Count(biospec.sample_barcode) as Sample_Count\nFROM `isb-cgc-bq.CCLE.clinical_current` clin\nLEFT JOIN `isb-cgc-bq.CCLE.biospecimen_current` biospec\nON clin.case_barcode = biospec.case_barcode\nGROUP BY clin.case_barcode\nHAVING Sample_Count > 1\nORDER BY clin.case_barcode",
                    //         "condition": "clin.case_barcode = biospec.case_barcode"
                    //     }
                    // ];
                },
                'render': function (data, type) {
                    let num_joins = data ? data.length: 0;
                    let display = num_joins == 0 ? '' :
                        '<div class="text-center"><a title="View List of Examples" class="useful-join-detail badge rounded-pill bqmeta-outline-badge">' + num_joins + '</a></div>';
                    return display;
                }
            },
            {
                'name': 'description',
                'data': function (row) {
                    return row.description ? row.description : '';
                },
                'visible': false
            },
            {
                'name': 'labels',
                'data': function (row) {
                    return row.labels ? row.labels : null;
                },
                'render': function (data, type) {
                    let labels_arr = $.map(data, function (v, k) {
                        if (type === 'display') {
                            return v ? k + ':' + v : k;
                        } else {
                            return v ? v : k;
                        }
                    });
                    return labels_arr.join(', ');
                },
                'visible': false
            },
            {
                'name': 'field_name',
                'data': function (row) {
                    return format_schema_field_names(row.schema.fields ? row.schema.fields : [], false);
                },
                'visible': false
            }
        ],
        serverSide: false,
        processing: true,
        order: [[1, 'asc']],
        language: {
            "infoFiltered": ""
        },
        initComplete: function (settings, json) {
            $('.dt-buttons').removeClass('btn-group');
            let show_details = (selected_filters['show_details'] == 'true');
            if (show_details & $('a.details-control').length>0){
                $('a.details-control').first().click();
            }
            window.history.pushState(null, 'BigQuery Table Search', query_param_url);
        },
        drawCallback: function (settings) {
            reset_table_style(settings);
            set_gcp_open_btn($('#bqmeta'));
        }

    });

    let updateSearch = function () {
        let filter_arr = [];
        $('.bq-filter').each(function () {
            let term = $(this).val();
            if (term !== '') {
                let column_name = $(this).attr('data-column-name');
                filter_arr.push(column_name + '=' + term);
            }
        });
        $('.bq-select').each(function () {
            let column_name = $(this).attr('data-column-name');
            let term = $(this).val();
            if (term.length > 0) {
                let col_filter;
                if ($(this).prop('multiple')) {
                    let regex_term = term.join('|');
                    col_filter = column_name + '=' + regex_term;
                } else {
                    col_filter = column_name + '=' + term;
                }
                filter_arr.push(col_filter);
            }
        });
        let checkbox_filters = {};
        $('input.bq-checkbox:checked').each(function () {
            let column_name = $(this).attr('data-column-name');
            let term = $(this).val();
            if (column_name in checkbox_filters) {
                checkbox_filters[column_name].push(term);
            } else {
                checkbox_filters[column_name] = [term];
            }
        });
        checkbox_filters['include_always_newest'] = [($('#include_always_newest').prop('checked') ? 'true':'false')];
        for (col in checkbox_filters) {
            filter_arr.push(col + '=' + checkbox_filters[col].join('|'))
        }
        let filter_str = filter_arr.join('&');
        let updated_url = "/search_api" + (filter_str ? '?' + filter_str : '');
        table.ajax.url(updated_url).load();
        window.history.pushState(null, 'BigQuery Table Search', filter_str ? ('?' + filter_str) : '/search');
        // window.history.pushState(null, 'BigQuery Table Search', filter_str ? ('?' + filter_str) : '');
    };

    $('.bq-filter').on('keyup', function () {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(updateSearch, doneTypingInterval);
    });

    $('.bq-checkbox, .bq-switch, .bq-select').on('change', function () {
        updateSearch();
    });

    $(".reset-btn").on('click', function () {
        $(".autocomplete_select_box").val('').trigger("chosen:updated");
        $('.bq-filter, .bq-select').val('');
        $('#status').val('current');
        $('#include_always_newest').prop('checked', false);
        $('.bq-checkbox').prop('checked', false);
        updateSearch();
    });

    $('#gcp-open-btn').on('click', function () {
        let do_not_show_again = ($('#do-not-show-cb:checked').length > 0);
        if (typeof (Storage) !== "undefined") {
            // Store
            gcp_modal_disabled |= do_not_show_again;
            sessionStorage.setItem("gcp_modal_disabled", gcp_modal_disabled);
        }
        $('#gcp-open-modal').modal('hide');
    });

    $('#bqmeta').find('tbody').on('click', 'td .tbl-preview', function () {
        let td = $(this).closest('td');
        let tr = $(this).closest('tr');
        let row = table.row(tr);
        let table_path = table.cell(td).data().id
        if (row.child.isShown()) {
            let reopen = !tr.hasClass('preview-shown');
            $('div.accordionSlider', row.child()).slideUp(400, function () {
                row.child.hide();
                tr.removeClass('shown details-shown preview-shown useful-join-shown versions-shown');
                tr.find('i.minus-control').hide();
                tr.find('i.plus-control').show();
                if (reopen){
                    show_tbl_preview(row, tr, td, table_path);
                }
            });
        } else {
            show_tbl_preview(row, tr, td, table_path);
        }
    });

    $('#bqmeta').find('tbody').on('click', 'td .view-versions', function () {
        let td = $(this).closest('td');
        let tr = $(this).closest('tr');
        let row = table.row(tr);
        if (row.child.isShown()) {
            let reopen = !tr.hasClass('versions-shown');
            $('div.accordionSlider', row.child()).slideUp(400, function () {
                row.child.hide();
                tr.removeClass('shown details-shown preview-shown useful-join-shown versions-shown')
                tr.find('i.minus-control').hide();
                tr.find('i.plus-control').show();
                if (reopen){
                    show_tbl_versions(row, tr, table.cell(td).data().releases);
                }
            });
        } else {
            show_tbl_versions(row, tr, table.cell(td).data().releases);
        }
    });


    $('#bqmeta').find('tbody').on('click', 'td .useful-join-detail', function () {
        let tr = $(this).closest('tr');
        let td = $(this).closest('td');
        let row = table.row(tr);
        let row_data = row.data();
        let tableReference = row_data['tableReference']
        let friendlyName = row_data['friendlyName']
        let joins_data = table.cell(td).data();
        let reopen = !tr.hasClass('useful-join-shown');
        if (row.child.isShown()) {
            $('div.accordionSlider', row.child()).slideUp(400, function () {
                row.child.hide();
                tr.removeClass('shown details-shown preview-shown useful-join-shown versions-shown');
                tr.find('i.minus-control').hide();
                tr.find('i.plus-control').show();
                if (reopen) {
                    show_useful_joins(row, tr, friendlyName, tableReference, joins_data);
                }
            });
        } else {
            // Open this row
            show_useful_joins(row, tr, friendlyName, tableReference, joins_data);
        }
    });

    // Add event listener for opening and closing details
    $('#bqmeta').find('tbody').on('click', 'a.details-control', function () {
        let tr = $(this).closest('tr');
        let row = table.row(tr);
        if (row.child.isShown()) {
            let reopen = !tr.hasClass('details-shown');
            $('div.accordionSlider', row.child()).slideUp(400, function () {
                row.child.hide();
                tr.removeClass('shown details-shown preview-shown useful-join-shown versions-shown')
                tr.find('i.minus-control').hide();
                tr.find('i.plus-control').show();
                if (reopen) {
                    show_tbl_details(row, tr);
                }
            });
        } else {
            show_tbl_details(row, tr)
        }
    });

    $('#bq-meta-form').find('i.fa-circle-info').tooltip();

    $(".autocomplete_select_box").chosen({
        no_results_text: "Oops, nothing found!",
        width: "100%"
    });
});


let set_filters = function () {
    let query_param_arr = [];
    let s_select_filters = ['status', 'projectId', 'reference_genome',]
    let m_select_filters = ['program',  'source', 'data_type', 'experimental_strategy']
    let text_filters = ['friendlyName', 'datasetId', 'tableId', 'description', 'field_name', 'labels'];
    let show_more_filters = ['projectId', 'datasetId', 'tableId', 'description', 'field_name', 'labels'];
    let show_all_filters = false;
    if (!('include_always_newest' in selected_filters)){
        selected_filters['include_always_newest'] = 'true';
    }
    for (const f in selected_filters) {
        if (s_select_filters.includes(f)) {
            $("select[data-column-name='" + f + "'] option").each(function () {
                for (let v of selected_filters[f]) {
                    if (is_quoted(v)) {
                        v = v.slice(1, -1);
                    }
                    if ($(this).val() === v) {
                        $(this).prop('selected', true);
                        break;
                    }
                }
            });
        } else if (m_select_filters.includes(f)) {
            $("select[data-column-name='" + f + "'] option").each(function () {
                let value_array = selected_filters[f];
                if (selected_filters[f][0].includes('|'))
                    value_array = selected_filters[f][0].split('|');
                for (let v of value_array) {
                    if (is_quoted(v)) {
                        v = v.slice(1, -1);
                    }
                    if ($(this).val() === v) {
                        $(this).prop('selected', true);
                        break;
                    }
                }
            });
        } else if (text_filters.includes(f)) {
            $("input[data-column-name='" + f + "']").val(selected_filters[f]);
        } else if (f === 'category') {
            $("input[data-column-name='" + f + "']").each(function () {
                $(this).prop('checked', selected_filters[f].includes($(this).val()));
            });
        } else if (f === 'include_always_newest') {
            $('#include_always_newest').prop('checked', selected_filters[f] == 'true');
        }
        if (!show_all_filters && show_more_filters.includes(f)) {
            show_all_filters = true;
            $('#show-btn').click();
        }
        for (let v of selected_filters[f]){
            query_param_arr.push(f + '=' + v);
        }
    }
    let query_param_url = (query_param_arr.length > 0 ? ('?' + query_param_arr.join('&')) : '');
    return query_param_url
}

let is_quoted = function (fieldVal) {
    if (fieldVal.length) {
        let singleQuotes = /^\'.*\'$/g.test(fieldVal);
        let doubleQuotes = /^\".*\"$/g.test(fieldVal);
        return singleQuotes | doubleQuotes;
    } else {
        return false;
    }
};


let show_tbl_details = function (row, tr) {
    row.child(format_tbl_details(row.data())).show();
    $(".copy-btn").on('click', function () {
        copy_to_clipboard($(this).siblings('.full_id_txt'));
    });
    // set_gcp_open_btn($(tr).next('tr').find('.detail-table'));
    tr.addClass('shown details-shown');
    $('div.accordionSlider', row.child()).slideDown();
    tr.find('i.minus-control').show();
    tr.find('i.plus-control').hide();
};


let show_tbl_versions = function (row, tr, data) {
    row.child(format_tbl_versions(data, row.data().id.replace(':','.'))).show();
    tr.addClass('shown versions-shown');
    $('div.accordionSlider', row.child()).slideDown();
};

let show_tbl_preview = function(row, tr, td, tbl_path) {
    // let tbl_path = table.cell(td).data().id;
    if (!td.data('preview-data')) {
        //check if the preview data is stored
        //if not get the data and store it
        $.ajax({
            type: "GET",
            url: "/get_tbl_preview/" + tbl_path + "/",
            beforeSend: function () {
                td.find('.preview-loading').show();
                td.find('.preview-icon').hide();

            },
            error: function (result) {
                let msg = 'There has been an error retrieving the preview table.';
                if (result.responseJSON && result.responseJSON.message) {
                    msg = result.responseJSON.message;
                }
                show_loaded_preview(row, tr, td, msg);
            },
            success: function (data) {
                td.data('preview-data', data);
                show_loaded_preview(row, tr, td);
            }
        });
    } else { // use the stored data to display
        show_loaded_preview(row, tr, td);
    }
};

let show_loaded_preview = function (row, tr, td, err_mssg) {
    if (err_mssg) {
        row.child('<div class="text-end"><i class="fa fa-exclamation-triangle" style="margin-right: 5px;"></i>' + err_mssg + '</div>').show();
    } else {
        let tbl_data = td.data('preview-data');
        row.child(format_tbl_preview(tbl_data['schema_fields'], tbl_data['tbl_data'])).show();
    }
    // tr.removeClass('details-shown');
    // tr.removeClass('useful-join-shown');
    // tr.removeClass('versions-shown');
    td.find('.preview-loading').hide();
    td.find('.preview-icon').show();

    tr.addClass('shown preview-shown');
    $('div.accordionSlider', row.child()).slideDown();
};

let show_useful_joins = function (row, tr, friendlyName, tableReference, joins_data) {
    row.child(format_useful_join_details(joins_data)).show();
    tr.next().find('.useful-join-view-btn').each(function (index) {
        let this_join_data = joins_data[index];
        this_join_data['tableName'] = friendlyName;//row_data['friendlyName'];
        this_join_data['tableId'] = formatFullId(tableReference, false);//row_data['tableReference'], false);
        $(this).data(this_join_data);
    });

    tr.next().find('.useful-join-view-btn').on('click', function () {
        let join_data = $(this).data();
        let tables = '';
        join_data['tables'].forEach(function (value, i) {
            let joinedTableRefs = get_joined_table_refs(value);
            tables += ('<li><a class="table-link" href="' + joinedTableRefs['table_url'] + '" title="Open in new tab">' + joinedTableRefs['formatted_id'] + '</a></li>');
        });
        let sql_query = join_data['sql'].replace('\n', '\n<br>');
        let dialog_content =
            '<div class="fw-bold fs-5">' + join_data['title'] + '</div>' +
            '<div>' + join_data['description'] + '</div>' +
            '<div class="fw-bold mt-3">Joined Table(s):</div><div><ul>' + tables + '</ul></div>' +
            '<div class="fw-bold">SQL Statement</div>' +
            '<div class="code-bg p-2"><div class="float-end"><button class="copy-query-btn btn" title="Copy to Clipboard">' +
            '<i class="fa-solid fa-copy"></i> Copy</button></div>' +
            '<pre><code class="language-sql query-body">' + sql_query + '</code></pre>' +
            '</div><div class="mt-2 fw-bold">Joined Condition</div><div class="p-2"><pre>' + join_data['condition'] + '</pre></div>';

        $('#useful-join-view-modal').find('.modal-body').html(dialog_content);
        Prism.highlightAll();
        $(".copy-query-btn").on('click', function () {
            copy_to_clipboard($(this).parents('.modal-body').find('.query-body'));
        });
        $('#useful-join-view-modal').find('.modal-sub-title').html(join_data['tableName']);
        $('#useful-join-view-modal').find('.modal-sub-sub-title').html(join_data['tableId']);
        $('#useful-join-view-modal').modal('show');
    });
    set_gcp_open_btn($(tr).next('tr').find('.detail-table'));
    tr.addClass('shown useful-join-shown');
    $('div.accordionSlider', row.child()).slideDown();
};

let format_bq_gcp_console_link = function (tbl_ref) {
    return 'https://console.cloud.google.com/bigquery'
        + '?p=' + tbl_ref.projectId
        + '&d=' + tbl_ref.datasetId
        + '&t=' + tbl_ref.tableId
        + '&page=table';
};


// Useful join table
let format_useful_join_details = function (d) {
    let join_table = '<div class="accordionSlider"><table class="useful-join-table">';
    join_table += '<thead><tr><th>Join Subject</th><th>Joined Tables</th><th></th></tr></thead>';
    // join_table += '<thead><tr><th style="width:200px">Join Subject</th><th style="width:400px">Joined Tables</th><th></th></tr></thead>';
    join_table += '<tbody>';
    d.forEach(join_info => {
        let tables = [];
        join_info['tables'].forEach(function (value, i) {
            let joinedTableRefs = get_joined_table_refs(value);
            tables.push('<div><a class="table-link" href="' + joinedTableRefs['table_url'] + '" title="Open in new tab">' + joinedTableRefs['formatted_id'] + '</a></div>');
        });
        join_table += '<tr>' +
            '<td>' + join_info['title'] + '</td>' +
            '<td>' + tables.join('<br>') + '</td>' +
            '<td><button class="badge useful-join-view-btn open-gcp-btn">View Details</button></td>' +
            '</tr>';
    });
    join_table += '</tbody></table></div>';
    return join_table;
};


let get_joined_table_refs = function (full_table_id) {
    let tableRefs = full_table_id.split(/[:.]/);
    let table_url = '/search?show_details=true&projectId=\'' + tableRefs[0] + '\'&datasetId=\'' + tableRefs[1] + '\'&tableId=\'' + tableRefs[2]+'\'';
    let formatted_id = tableRefs.join('.');
    return {
        'table_url': table_url,
        'formatted_id': formatted_id
    }
};


let format_tbl_details = function (d) {
    // `d` is the original data object for the row
    return '<div class="accordionSlider"><table class="detail-table">' +
        '<td style="vertical-align:top;"><strong>Full ID</strong></td>' +
        '<td>' +
        '<span class="full_id_txt">' + formatFullId(d.tableReference, false) +
        '</span>' +
        '<button class="copy-btn btn" title="Copy to Clipboard">' +
        '<i class="fa-solid fa-copy" aria-hidden="true"></i>' +
        'Copy' +
        '</button>' +
        // '<button data-gcpurl="' + format_bq_gcp_console_link(d.tableReference) + '" class="open-gcp-btn" style="margin-left: 0;" title="Open in Google Cloud Console">' +
        // '<svg id="BIGQUERY_SECTION_cache12" fill="none" fill-rule="evenodd" height="11" viewBox="0 0 32 32" width="11" xmlns="http://www.w3.org/2000/svg" fit="" preserveAspectRatio="xMidYMid meet" focusable="false">' +
        // '<path d="M8.627 14.358v3.69c.58.998 1.4 1.834 2.382 2.435v-6.125H8.62z" fill="#19424e"></path>' +
        // '<path d="M13.044 10.972v10.54c.493.073.998.12 1.516.12.473 0 .934-.042 1.386-.104V10.972h-2.902z" fill="#3A79B8"></path>' +
        // '<path d="M18.294 15.81v4.604a6.954 6.954 0 0 0 2.384-2.556v-2.05h-2.384zm5.74 6.233l-1.99 1.992a.592.592 0 0 0 0 .836L27 29.83c.23.23.606.23.836 0l1.992-1.99a.594.594 0 0 0 0-.837l-4.957-4.956a.593.593 0 0 0-.83 0" fill="#3A79B8"></path>' +
        // '<path d="M14.615 2C7.648 2 2 7.648 2 14.615 2 21.582 7.648 27.23 14.615 27.23c6.966 0 12.614-5.648 12.614-12.615C27.23 7.648 21.58 2 14.61 2m0 21.96a9.346 9.346 0 0 1-9.346-9.345 9.347 9.347 0 1 1 9.346 9.346" fill="#3A79B8"></path></svg>' +
        // 'OPEN' +
        // '</button>' +

        '</td>' +
        '</tr><tr>' +
        '<td style="vertical-align:top;"><strong>Dataset ID</strong></td>' +
        '<td>' + d.tableReference.datasetId + '</td>' +
        '</tr><tr>' +
        '<td style="vertical-align:top;"><strong>Table ID</strong></td>' +
        '<td>' + d.tableReference.tableId + '</td>' +
        '</tr><tr>' +
        '<td style="vertical-align:top;"><strong>Description</strong></td>' +
        '<td>' + (d.description == null ? 'N/A' : d.description) + '</td>' +
        '</tr><tr>' +
        '<td><strong>Schema</strong></td>' +
        '<td>' + form_schema_table(d.schema.fields ? d.schema.fields : []) + '</td>' +
        '</tr><tr>' +
        '<td><strong>Labels</strong></td>' +
        '<td>' + tokenize_labels(d.labels) + '</td>' +
        '</tr></table></div>';
};


let formatFullId = function (tblRef, wrapText) {
    return (wrapText ? '`' : '') + tblRef.projectId + '.' + tblRef.datasetId + '.' + tblRef.tableId + (wrapText ? '`' : '');
};


let copy_to_clipboard = function (el) {
    navigator.clipboard.writeText(el.text());
};

const sortAlphaNum = (a, b) => a.localeCompare(b, 'en', {numeric: true})

let format_tbl_versions = function (versions_data, row_table_id) {
    let html_tbl = '<div class="accordionSlider"><table class="versions-table">';
    html_tbl += '<tr><th class="px-2">Version</th><th class="px-2">Table</th><th class="px-2">Type</th></tr>';
    for (let d of Object.keys(versions_data).sort(sortAlphaNum).reverse()) {
        html_tbl += '<tr><td class="px-2">' + d + (versions_data[d].is_latest ? "<span class='ms-2 badge rounded-pill bg-secondary'>Latest</span>" : "");
        html_tbl += '</td><td class="px-2">';
        let table_link_list = [];
        let type_list = [];
        for (let t of versions_data[d].tables) {
            let refs = get_joined_table_refs(t);
            table_link_list.push((row_table_id == refs.formatted_id ? '<span class="text-secondary"><i class="fa-solid fa-arrow-right pe-1"></i></span>':'<span class="pe-2">&nbsp;&nbsp;</span>')+'<a class="table-link" rel="noreferrer" target="_blank" href="' + refs.table_url + '">' + refs.formatted_id + '</a>');
            type_list.push(refs.formatted_id.endsWith('_current') ? 'Always Newest': 'Stable');
        }
        html_tbl += table_link_list.join('<br/>');
        html_tbl += '</td><td class="px-2">';
        html_tbl += type_list.join('<br/>');
        html_tbl += '</td></tr>';
    }
    html_tbl += '</table></div>';
    return html_tbl;
};

let format_tbl_preview = function (schema_fields, rows) {
    let html_tbl = '<div class="accordionSlider preview-table-container"><table class="preview-table">';
    html_tbl += '<tr>';
    html_tbl += format_schema_field_names(schema_fields, true);
    html_tbl += '</tr>';
    html_tbl += format_tbl_preview_body(schema_fields, rows);
    html_tbl += '</table></div>';
    return html_tbl;
};


let format_schema_field_names = function (schema_fields, in_html) {
    let schema_field_names_str = '';
    if (schema_fields) {
        for (let col = 0; col < schema_fields.length; col++) {
            if (schema_fields[col]['type'] === 'RECORD') {
                let nested_fields = schema_fields[col]['fields'];
                for (let n_col = 0; n_col < nested_fields.length; n_col++) {
                    if (nested_fields[n_col]['type'] === 'RECORD') {
                        let double_nested_fields = nested_fields[n_col]['fields'];
                        for (let nn_col = 0; nn_col < double_nested_fields.length; nn_col++) {
                            schema_field_names_str += (in_html ? '<th>' : '') + schema_fields[col]['name'] + '.'
                                + nested_fields[n_col]['name'] + '.'
                                + double_nested_fields[nn_col]['name']
                                + (in_html ? '</th>' : ', ');
                        }
                    } else {
                        schema_field_names_str += (in_html ? '<th>' : '') + schema_fields[col]['name'] + '.' + nested_fields[n_col]['name'] + (in_html ? '</th>' : ', ');
                    }

                }
            } else {
                schema_field_names_str += (in_html ? '<th>' : '') + schema_fields[col]['name'] + (in_html ? '</th>' : ', ');
            }
        }
        if (schema_field_names_str.substring(-2) === ', ') { // remove the last comma
            schema_field_names_str = schema_field_names_str.slice(0, -2);
        }
    }
    return schema_field_names_str;
};


let format_tbl_preview_body = function (schema_fields, rows) {
    let tbody_str = '';
    for (let row = 0; row < rows.length; row++) {
        tbody_str += '<tr>';
        for (let c = 0; c < schema_fields.length; c++) {
            let col = schema_fields[c]['name'];
            let cell = rows[row][col];
            if (schema_fields[c]['type'] === 'RECORD' || schema_fields[c]['mode'] === 'REPEATED') {
                let nested_fields_len = schema_fields[c]['type'] === 'RECORD' ? schema_fields[c]['fields'].length : 1;
                for (let n_col = 0; n_col < nested_fields_len; n_col++) {
                    let n_col_name = (schema_fields[c]['fields'] ? schema_fields[c]['fields'][n_col]['name'] : null);
                    if ('fields' in schema_fields[c] && schema_fields[c]['fields'][n_col]['type'] === 'RECORD') {
                        let n_nested_fields_len = schema_fields[c]['fields'][n_col]['fields'].length;
                        for (let nn_col = 0; nn_col < n_nested_fields_len; nn_col++) {
                            let nn_col_name = schema_fields[c]['fields'][n_col]['fields'][nn_col]['name'];
                            tbody_str += nest_table_cell(cell, n_col_name, nn_col_name);
                        }
                    } else {
                        tbody_str += nest_table_cell(cell, n_col_name);
                    }
                }
            } else {
                tbody_str += '<td nowrap>' + cell + '</td>';
            }
        }
        tbody_str += '</tr>';
    }
    return tbody_str;
};


let nest_table_cell = function (cell, n_col_name, nn_col_name) {
    let MAX_NESTED_ROW = 5;
    let truncate_rows = cell.length > MAX_NESTED_ROW;
    let td_str = '<td nowrap><table>';
    if (cell) {
        for (let n_row = 0; n_row < (truncate_rows ? MAX_NESTED_ROW : cell.length); n_row++) {
            td_str += '<tr><td nowrap>';
            if (truncate_rows && n_row == MAX_NESTED_ROW - 1) {
                cell[n_row] = '<i class="fa fa-ellipsis-v" aria-hidden="true" style="margin-left: 5px;" title="' + (cell.length - MAX_NESTED_ROW + 1) + ' rows are truncated for preview."></i>';
            }
            if (typeof cell[n_row] === 'object') {
                if (nn_col_name != null) {
                    if (cell[n_row][n_col_name] != null && cell[n_row][n_col_name].length) {
                        td_str += (cell[n_row][n_col_name][0][nn_col_name] != null ? cell[n_row][n_col_name][0][nn_col_name] : '&nbsp;');
                    } else {
                        td_str += '&nbsp;';
                    }
                } else {
                    let n_cell = cell[n_row][n_col_name];
                    if (n_cell && typeof n_cell === 'object') {
                        td_str += '[' + ($.map(n_cell, function (nn_row) {
                            return nn_row;
                        }).join(', ')) + ']';
                    } else {
                        td_str += n_cell;
                    }
                }
            } else {
                td_str += cell[n_row];
            }
            td_str += '</td></tr>';
        }
    } else {
        td_str += '<tr><td></td></td>';
    }
    td_str += '</table></td>';
    return td_str;
};


let tokenize_labels = function (labels_obj) {
    let tokenized_str = '';
    $.each(labels_obj, function (key, value) {
        tokenized_str += '<span class="label">' + key + (value ? ' : ' + value : '') + '</span>';
    });
    return tokenized_str;
};


let form_schema_table = function (data) {
    let schema_table = '<table class="schema-table">';
    if (data) {
        schema_table += '<tr><th>Field Name</th><th>Type</th><th>Mode</th><th>Description</th></tr>'
    }
    $.each(data, function (i, d) {
        schema_table += '<tr><td>' + d.name + '</td><td>' + d.type + '</td><td>' + d.mode + '</td><td>' + d.description + '</td></tr>';
        if (d.type === 'RECORD') {
            $.each(d.fields, function (ii, dd) {
                schema_table += '<tr><td>&nbsp;&nbsp;&nbsp;&nbsp;.' + dd.name + '</td><td>' + dd.type + '</td><td>' + dd.mode + '</td><td>' + dd.description + '</td></tr>';
                if (dd.type === 'RECORD') {
                    $.each(dd.fields, function (iii, ddd) {
                        schema_table += '<tr><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;.' + ddd.name + '</td><td>' + ddd.type + '</td><td>' + ddd.mode + '</td><td>' + ddd.description + '</td></tr>';
                    });
                }
            });
        }
    });
    schema_table += '</table>';
    return schema_table;
};


let filtered_label_data = function (data_labels, filter_key_term) {
    let filtered_val_arr = $.map(data_labels, function (val, key) {
        return key.startsWith(filter_key_term) ? val : null;
    });
    return (filtered_val_arr.length > 0 ? filtered_val_arr.join(', ') : null);
};


let format_label_display = function (data, type) {
    return (type === 'display' && data) ?
        data.toUpperCase().replace(/_/g, ' ') : data;
};


let reset_table_style = function (settings) {
    $('#bqmeta').find('th').attr('style', '');
    let api = new $.fn.dataTable.Api(settings);
    let csv_button = api.buttons('.buttons-csv');
    if (api.rows({filter: 'applied'}).data().length === 0) {
        csv_button.disable();
    } else {
        csv_button.enable();
    }
    if (bq_total_entries > api.rows().data().length) {
        $('#bqmeta_info').append(' (filtered from ' + (bq_total_entries).toLocaleString("en-US") + ' total entries)');
    }

};


let set_gcp_open_btn = function (selection) {
    $(selection).find(".open-gcp-btn").on('click', function () {
        $('#gcp-open-btn').attr('href', $(this).data('gcpurl'));
        if (typeof (Storage) !== "undefined") {
            gcp_modal_disabled |= sessionStorage.getItem("gcp_modal_disabled") == "true";
        }
        if (!gcp_modal_disabled) {
            $('#gcp-open-modal').modal('show');
        } else {
            $('#gcp-open-btn')[0].click();
        }
    });
};
