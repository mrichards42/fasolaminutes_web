$('#minutes-search').on('input', function() {
    var match = ($(this).val()).match(/^\((\d+)\)/);
    if (match && minutes_id !== match[1])
        window.location = '/edit/' + match[1];
});

if (minutes_id) {
    $.getJSON('/edit/data/' + minutes_id, function(data) {

        var $editor = $('#editor');

        function pageNumRenderer(instance, td, row, col, prop, value, cellProperties) {
            Handsontable.renderers.TextRenderer.apply(this, arguments);
            var match = value.match(/^(\d+)[tb]?/);
            if (match) {
                pad = Math.max(0, 3 - match[1].length)
                pad += 0.5
                td.style.paddingLeft = pad + 'ex'
            }
        }

        var hot = new Handsontable($editor[0], {
            data: data,
            rowHeaders: true,
            colHeaders: ['Page', 'Leader', 'Recording URL'],
            cells: function(row, col, prop) {
                if (col === 0)
                    return {renderer: pageNumRenderer};
            }
        });
        console.log('got data');
    });
}