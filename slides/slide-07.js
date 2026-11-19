const path = require('path');
const NOTES = require('./notes');
const { addMappedText, addMappedShape, addMappedImage } = require('/workspace/.plugin-cache/sha256-tree-v1-6562a7a9a9a69af61724f6f5a3cf2b2049410641553731506ce9071693edf57c/skills/pptx/scripts/mavis-ppt-map.cjs');

const fs = require('fs');
const FIG = path.join(__dirname, '..', 'figures');
const DATA_FILE = path.join(__dirname, 'data', 'results.json');

// The measured numbers come from scripts/make_slide_data.py.  Simulated
// (offline) results are refused on purpose: they must never reach the
// presentation.
function loadResults() {
  try {
    const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    if (data && data.backend === 'offline') {
      console.warn('slide-07: refusing simulated (offline) results');
      return null;
    }
    return data;
  } catch (err) {
    return null;
  }
}
const GOLD = 'E9C46A';
const SAND = 'F4A261';

function pageNumber(slide, map, n, theme) {
  addMappedText(slide, map, {
    elementId: 'page.number.' + n, role: 'pageNumber', text: String(n),
    x: 9.3, y: 5.08, w: 0.45, h: 0.3,
    options: { fontSize: 10, color: theme.secondary, align: 'right', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-%s.js', method: 'addText' },
  });
}

function title(slide, map, id, text, theme) {
  addMappedText(slide, map, {
    elementId: id, role: 'title', text: text,
    x: 0.55, y: 0.34, w: 8.9, h: 0.6,
    options: { fontSize: 27, bold: true, color: theme.primary, align: 'left',
               margin: 0, fontFace: 'Arial', fit: 'shrink' },
    source: { file: 'slides/slide-%s.js', method: 'addText' },
  });
}


function createSlide(pres, theme) {
  const slide = pres.addSlide();
  const map = pres.__mavisElementMap;
  map?.startSlide({ slideNumber: 7, slideId: 'results', title: 'Main results' });
  title(slide, map, 'results.title', 'Main results over 25 scenarios', theme);

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'results.figure.shell', role: 'card',
    x: 0.5, y: 1.05, w: 5.35, h: 3.85,
    options: { fill: { color: 'FFFFFF' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-07.js', method: 'addShape' },
  });
  addMappedImage(slide, map, {
    elementId: 'results.figure.image', role: 'image',
    path: path.join(FIG, 'fig1_main_metrics.png'),
    x: 0.62, y: 1.17, w: 5.1, h: 3.6,
    source: { file: 'slides/slide-07.js', method: 'addImage' },
  });

  const head = ['Method', 'Safety', 'Viab.', 'Dual', 'Compl.', 'OoDB'];
  const measured = loadResults();
  const rows = [
    ['B1 zero-shot', '-', '-', '-', '-', '-'],
    ['B2 naive RAG', '-', '-', '-', '-', '-'],
    ['Proposed agent', '-', '-', '-', '-', '-'],
  ];
  if (measured) {
    const pick = (label) => (measured.rows || []).find((r) => r.method === label);
    const order = [['B1 zero-shot', 'B1 zero-shot'],
                   ['B2 naive RAG', 'B2 naive RAG'],
                   ['Proposed agent', 'Proposed agent']];
    order.forEach(([label], i) => {
      const r = pick(label);
      if (!r) return;
      rows[i] = [r.method, r.safety, r.viability, r.dual, r.completeness, r.oodb];
    });
  }
  const colX = [6.12, 7.42, 7.82, 8.2, 8.58, 9.0];
  const colW = [1.28, 0.4, 0.38, 0.38, 0.42, 0.4];
  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'results.table.card', role: 'card',
    x: 6.0, y: 1.05, w: 3.5, h: 2.5,
    options: { fill: { color: 'F6F7F6' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-07.js', method: 'addShape' },
  });
  head.forEach((h, j) => {
    addMappedText(slide, map, {
      elementId: 'results.table.head.' + j, role: 'label', text: h,
      x: colX[j], y: 1.2, w: colW[j], h: 0.26,
      options: { fontSize: 8.5, bold: true, color: theme.primary, align: j === 0 ? 'left' : 'center',
                 margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-07.js', method: 'addText' },
    });
  });
  rows.forEach((r, i) => {
    const y = 1.55 + i * 0.42;
    if (i === 2) {
      addMappedShape(slide, map, pres.shapes.RECTANGLE, {
        elementId: 'results.table.row.' + i + '.band', role: 'decorative',
        x: 6.12, y: y - 0.04, w: 3.34, h: 0.36,
        options: { fill: { color: 'E3EFE9' }, line: { color: 'E3EFE9', width: 0 } },
        source: { file: 'slides/slide-07.js', method: 'addShape' },
      });
    }
    r.forEach((v, j) => {
      addMappedText(slide, map, {
        elementId: 'results.table.cell.' + i + '.' + j, role: 'body', text: v,
        x: colX[j], y: y, w: colW[j], h: 0.28,
        options: { fontSize: 10, bold: i === 2, color: theme.primary,
                   align: j === 0 ? 'left' : 'center', margin: 0, fontFace: 'Arial' },
        source: { file: 'slides/slide-07.js', method: 'addText' },
      });
    });
  });
  addMappedText(slide, map, {
    elementId: 'results.table.note', role: 'body',
    text: (measured
      ? `Source: results/${measured.run}/summary.csv  (${measured.model}, ${measured.n_scenarios} scenarios)\n`
        + 'Safety = pet-safety compliance, Viab. = horticultural viability, '
        + 'Compl. = design completeness 0-15, O-o-DB = out-of-database rate.'
      : 'Fill from results/summary.csv\nSafety = pet-safety compliance, Viab. = horticultural viability, Compl. = design completeness 0-15, O-o-DB = out-of-database rate.'),
    x: 6.18, y: 2.92, w: 3.2, h: 0.6,
    options: { fontSize: 8.5, color: '6B7973', align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.1, fontFace: 'Arial' },
    source: { file: 'slides/slide-07.js', method: 'addText' },
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'results.finding.card', role: 'card',
    x: 6.0, y: 3.65, w: 3.5, h: 1.25,
    options: { fill: { color: theme.primary }, line: { color: theme.primary, width: 0 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-07.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'results.finding.text', role: 'body',
    text: 'The agent\'s pet-safety compliance is exactly 100%, because the filter is deterministic -- the model is never given the opportunity to pick an unsafe species.',
    x: 6.22, y: 3.82, w: 3.1, h: 0.95,
    options: { fontSize: 10.5, color: 'FFFFFF', align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.1, fontFace: 'Arial' },
    source: { file: 'slides/slide-07.js', method: 'addText' },
  });
  pageNumber(slide, map, 7, theme);
  slide.addNotes(NOTES['07']);
}

module.exports = { createSlide };
