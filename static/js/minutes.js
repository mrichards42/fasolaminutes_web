$(function() {
    // Handsontable element
    var $wrapper = $('#leads-wrapper');
    var $editor = $('#leads-table');
    var hot;

    // Keep handsontable size consistent as the user resizes the panes
    var resizeHot = _.debounce(function() {
        hot.updateSettings({
            width: $wrapper.width(),
            height: $wrapper.height()
        });
    }, 10);
    $wrapper.on('resize', resizeHot);
    $(window).on('resize', resizeHot);

    // Add split
    var splitter = Split(['#minutes-wrapper', '#leads-wrapper'], {
        size: [50, 50],
        onDrag: resizeHot
    });

    // Munge leads data
    var data = JSON.parse($('#leads-json').html());
    var leads = data.leads;
    var minutes_id = data.minutes_id;
    leads.forEach(function(lead) {
        if (! lead.original)
            lead.original = { song: lead.song, leader: lead.leader };
    });

    // Render page numbers right-aligned on the number (ignore t/b)
    function pageNumRenderer(instance, td, row, col, prop, value, cellProperties) {
        Handsontable.renderers.TextRenderer.apply(this, arguments);
        var match = value ? value.match(/^(\d+)[tb]?/) : null;
        if (match) {
            pad = Math.max(0, 3 - match[1].length)
            pad += 0.5
            td.style.paddingLeft = pad + 'ex'
        }
    }

    function diffRenderer(field) {
        return function(instance, td, row, col, prop, value, cellProperties) {
            Handsontable.renderers.TextRenderer.apply(this, arguments);
            if (leads[row][field] !== leads[row]['original'][field]) {
                td.style.background = 'pink';
            } else {
                delete td.style.background;
            }
        }
    }

    var songDiffRenderer = diffRenderer('song');
    var leaderDiffRenderer = diffRenderer('leader');

    // Autocomplete names
    var leaderNames = []
    function updateAutocomplete() {
        // Make a set of all leader names
        var names = {};
        leads.forEach(function(lead) {
            names[lead.leader || ''] = 1;
            names[lead.original.leader || ''] = 1;
        });
        // Update leaderNames array
        leaderNames.splice(0);
        [].push.apply(leaderNames, Object.keys(names));
        console.log('updated autocomplete', leaderNames);
    }
    updateAutocomplete();

    hot = new Handsontable($editor[0], {
        data: leads,
        width: $wrapper.width(),
        height: $wrapper.height(),
        stretchH: 'all',
        rowHeaders: false,
        colHeaders: ['Song', 'Leader', 'Parsed Song', 'Parsed Leader'],
        columns: [
            {
                data: 'song',
                renderer: function() {
                    pageNumRenderer.apply(this, arguments);
                    songDiffRenderer.apply(this, arguments)
                }
            },
            {
                data: 'leader',
                type: 'autocomplete',
                source: leaderNames,
                renderer: leaderDiffRenderer
            },
            {
                data: 'original.song',
                editor: false,
                renderer: pageNumRenderer
            },
            {
                data: 'original.leader',
                editor: false
            },
        ],
        contextMenu: ['row_above', 'row_below', 'remove_row'],
        cells: function(row, col, prop) {
            if (col === 0)
                return {renderer: function(instance, td, row, col, prop, value, cellProperties) {
                    pageNumRenderer.apply(this, arguments);
                    if (leads[row].song !== leads[row].original.song) {
                        td.style.background = 'pink';
                    } else {
                        delete td.style.background;
                    }
                }};
        },
        afterChange: function(changes) {
            if (changes) {
                for (var i=0; i<changes.length; ++i) {
                    // Check that something actually changed
                    // indexes 2 and 3 are oldValue, newValue
                    if (changes[i][2] !== changes[i][3]) {
                        console.log('got changes', changes)
                        updateAutocomplete();
                        return;
                    }
                }
                console.log('NO CHANGES', changes)
            }
        },
        afterRemoveRow: function() {
            updateAutocomplete()
        },
        afterAddRow: function() {
            updateAutocomplete()
        },
        afterSelection: function(rowStart, colStart, rowEnd, colEnd) {
            // Highlight the tokens in the selected rows
            $('.token-selected').removeClass('token-selected');
            var start = Math.min(rowStart, rowEnd);
            var end = Math.max(rowStart, rowEnd);
            for (var row = start; row <=  end; row++) {
                var lead = leads[row] || {};
                var leader = lead.leader_id;
                var song = lead.song_id;
                if (leader && song) {
                    $('#token-' + leader + ',#token-' + song).addClass('token-selected');
                }
            }
        }
    });
    //HOT = hot;
});