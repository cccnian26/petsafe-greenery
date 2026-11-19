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
  map?.startSlide({ slideNumber: 9, slideId: 'limitations', title: 'Limitations and outlook' });
  title(slide, map, 'limitations.title', 'Limitations and outlook', theme);

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'limitations.left.card', role: 'card',
    x: 0.55, y: 1.1, w: 4.35, h: 3.8,
    options: { fill: { color: 'FBF0ED' }, line: { color: theme.accent, width: 1 }, rectRadius: 0.06 },
    source: { file: 'slides/slide-09.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'limitations.left.heading', role: 'heading', text: 'Limitations I want to state myself',
    x: 0.8, y: 1.3, w: 3.85, h: 0.34,
    options: { fontSize: 14, bold: true, color: theme.accent, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-09.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'limitations.left.body', role: 'body',
    text: '150 of 1000+ listed species\nCats and dogs only\n25 scenarios -- a defensible scale, not a large one\nA mis-parsed brief propagates into the candidate pool\nThe guarantee covers species in the database; the out-of-database rate is reported separately',
    x: 0.8, y: 1.72, w: 3.85, h: 2.9,
    options: { fontSize: 11.5, color: theme.primary, align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.28, fontFace: 'Arial' },
    source: { file: 'slides/slide-09.js', method: 'addText' },
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'limitations.right.card', role: 'card',
    x: 5.15, y: 1.1, w: 4.35, h: 3.8,
    options: { fill: { color: 'F1F7F4' }, line: { color: theme.secondary, width: 1 }, rectRadius: 0.06 },
    source: { file: 'slides/slide-09.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'limitations.right.heading', role: 'heading', text: 'What comes next',
    x: 5.4, y: 1.3, w: 3.85, h: 0.34,
    options: { fontSize: 14, bold: true, color: theme.secondary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-09.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'limitations.right.body', role: 'body',
    text: 'Dense recall + deterministic filtering\nPer-species provenance shown in the answer\nIterative tool use with iterative auditing\nMore species, more pets, more site types\n\nThe takeaway: swap in a stronger LLM and the design gets prettier; the toxicity guarantee does not move.',
    x: 5.4, y: 1.72, w: 3.85, h: 2.9,
    options: { fontSize: 11.5, color: theme.primary, align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.28, fontFace: 'Arial' },
    source: { file: 'slides/slide-09.js', method: 'addText' },
  });
  pageNumber(slide, map, 9, theme);
  slide.addNotes(NOTES['09']);
}

module.exports = { createSlide };
