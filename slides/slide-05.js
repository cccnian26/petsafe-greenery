const path = require('path');
const NOTES = require('./notes');
const { addMappedText, addMappedShape, addMappedImage } = require('/workspace/.plugin-cache/sha256-tree-v1-6562a7a9a9a69af61724f6f5a3cf2b2049410641553731506ce9071693edf57c/skills/pptx/scripts/mavis-ppt-map.cjs');

const FIG = path.join(__dirname, '..', 'figures');
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
  map?.startSlide({ slideNumber: 5, slideId: 'groundtruth', title: 'Ground truth and rules' });
  title(slide, map, 'groundtruth.title', 'Ground truth and the decision rules', theme);

  const kpis = [
    ['150', 'species in the\nground-truth database'],
    ['25', 'benchmark\nscenarios'],
    ['3', 'methods compared\nunder one contract'],
    ['5', 'deterministic\nmetrics'],
  ];
  kpis.forEach((k, i) => {
    const x = 0.55 + i * 2.32;
    addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
      elementId: 'groundtruth.kpi.' + (i + 1) + '.card', role: 'card',
      x: x, y: 1.05, w: 2.12, h: 1.12,
      options: { fill: { color: 'F6F7F6' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.06 },
      source: { file: 'slides/slide-05.js', method: 'addShape' },
    });
    addMappedText(slide, map, {
      elementId: 'groundtruth.kpi.' + (i + 1) + '.value', role: 'value', text: k[0],
      x: x + 0.18, y: 1.14, w: 1.76, h: 0.42,
      options: { fontSize: 26, bold: true, color: theme.secondary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-05.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: 'groundtruth.kpi.' + (i + 1) + '.label', role: 'label', text: k[1],
      x: x + 0.18, y: 1.62, w: 1.76, h: 0.5,
      options: { fontSize: 9, color: '51605A', align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.05, fontFace: 'Arial' },
      source: { file: 'slides/slide-05.js', method: 'addText' },
    });
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'groundtruth.safety.card', role: 'card',
    x: 0.55, y: 2.4, w: 4.4, h: 2.55,
    options: { fill: { color: 'FBF0ED' }, line: { color: theme.accent, width: 1 }, rectRadius: 0.06 },
    source: { file: 'slides/slide-05.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'groundtruth.safety.heading', role: 'heading', text: 'Safety rule -- never relaxed',
    x: 0.8, y: 2.58, w: 3.9, h: 0.34,
    options: { fontSize: 14, bold: true, color: theme.accent, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-05.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'groundtruth.safety.body', role: 'body',
    text: 'A species toxic to any pet in the household is removed before the model ever sees the candidate list.\n\nToxicity labels come from the ASPCA Animal Poison Control database, one source URL per species.',
    x: 0.8, y: 2.98, w: 3.9, h: 1.8,
    options: { fontSize: 11.5, color: theme.primary, align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.15, fontFace: 'Arial' },
    source: { file: 'slides/slide-05.js', method: 'addText' },
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'groundtruth.viability.card', role: 'card',
    x: 5.15, y: 2.4, w: 4.35, h: 2.55,
    options: { fill: { color: 'F1F7F4' }, line: { color: theme.secondary, width: 1 }, rectRadius: 0.06 },
    source: { file: 'slides/slide-05.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'groundtruth.viability.heading', role: 'heading', text: 'Viability rule -- relaxable, and reported',
    x: 5.4, y: 2.58, w: 3.85, h: 0.34,
    options: { fontSize: 14, bold: true, color: theme.secondary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-05.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'groundtruth.viability.body', role: 'body',
    text: 'Light is stored as the darkest light a plant tolerates: full shade < bright indirect < partial shade < full sun. A plant is viable when the site is at least as bright as its tolerance.\n\nIf the strict query is empty, moisture is relaxed first, then light -- and the relaxation is reported to the user.',
    x: 5.4, y: 2.98, w: 3.85, h: 1.85,
    options: { fontSize: 11, color: theme.primary, align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.12, fontFace: 'Arial' },
    source: { file: 'slides/slide-05.js', method: 'addText' },
  });
  pageNumber(slide, map, 5, theme);
  slide.addNotes(NOTES['05']);
}

module.exports = { createSlide };
