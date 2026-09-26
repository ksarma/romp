// stub: the viewer's width observer and the Comments panel's two sizers (file-comments.ts: the sizer and the card sizer), each picked
// by its callback, are inert; the viewer's tables' observer and its figures' observer still run
(function () { var RO = window.ResizeObserver, INERT = ["width", "sizer", "cards"]; window.__roInert = 0; window.__roMade = 0; window.__roKinds = [];
  var kind = function (cb) { var s = String(cb);   // the pane's observers told apart by their callbacks, never by the order they are made in
    if (/hideFloatOnScroll/.test(s)) return "sizer";                                    // file-comments.ts: the panel's sizer
    if (/^\(\)\s*=>\s*this\.scheduleLayout\(\)$/.test(s.trim())) return "cards";         // file-comments.ts: its card sizer
    if (/--fv-table-w/.test(s)) return "tables";                                         // file-view.ts watchBodyWidth: the tables' observer
    if (/\.clientWidth\b/.test(s) && /contentRect\.width/.test(s)) return "width";       // file-view.ts watchBodyWidth: the body's width observer
    if (/contentRect\.height === 0/.test(s)) return "figures";                           // file-view.ts watchFigureBoxes: the figures' observer
    return "other"; };
  window.ResizeObserver = function (cb) { var k = kind(cb); window.__roMade++; window.__roKinds.push(k);
    if (INERT.indexOf(k) >= 0) { window.__roInert++; return { observe: function () {}, unobserve: function () {}, disconnect: function () {} }; } return new RO(cb); };
  window.ResizeObserver.prototype = RO.prototype; })();
