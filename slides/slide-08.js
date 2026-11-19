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
  map?.startSlide({ slideNumber: 8, slideId: 'completeness', title: 'Design completeness' });
  title(slide, map, 'completeness.title', 'Design quality is a separate axis from safety', theme);

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'completeness.figure.shell', role: 'card',
    x: 0.5, y: 1.05, w: 5.35, h: 3.85,
    options: { fill: { color: 'FFFFFF' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-08.js', method: 'addShape' },
  });
  addMappedImage(slide, map, {
    elementId: 'completeness.figure.image', role: 'image',
    path: path.join(FIG, 'fig6_rubric_items.png'),
    x: 0.62, y: 1.17, w: 5.1, h: 3.6,
    source: { file: 'slides/slide-08.js', method: 'addImage' },
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'completeness.rubric.card', role: 'card',
    x: 6.0, y: 1.05, w: 3.5, h: 2.15,
    options: { fill: { color: 'F1F7F4' }, line: { color: theme.secondary, width: 1 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-08.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'completeness.rubric.heading', role: 'heading', text: 'The rubric is code, not opinion',
    x: 6.22, y: 1.2, w: 3.1, h: 0.32,
    options: { fontSize: 13, bold: true, color: theme.secondary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-08.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'completeness.rubric.body', role: 'body',
    text: '15 binary items, each with a stored detection rule:\n\nA1-A3  three spatial zones (vertical, ground, pet-accessible)\nC2-C3  watering frequency + light position  ->  core score 0-5\n\nA vague mention scores nothing.',
    x: 6.22, y: 1.56, w: 3.1, h: 1.55,
    options: { fontSize: 10, color: theme.primary, align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.08, fontFace: 'Arial' },
    source: { file: 'slides/slide-08.js', method: 'addText' },
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'completeness.contract.card', role: 'card',
    x: 6.0, y: 3.3, w: 3.5, h: 1.6,
    options: { fill: { color: theme.primary }, line: { color: theme.primary, width: 0 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-08.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'completeness.contract.heading', role: 'heading', text: 'A design must also explain itself',
    x: 6.22, y: 3.44, w: 3.1, h: 0.3,
    options: { fontSize: 12.5, bold: true, color: GOLD, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-08.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'completeness.contract.body', role: 'body',
    text: 'spatial structure  /  combination logic  /  care instructions  /  care cautions -- each with a per-item failure list fed back to the model for one repair round.',
    x: 6.22, y: 3.76, w: 3.1, h: 1.0,
    options: { fontSize: 10, color: 'E4EDE8', align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.1, fontFace: 'Arial' },
    source: { file: 'slides/slide-08.js', method: 'addText' },
  });
  pageNumber(slide, map, 8, theme);
  slide.addNotes(NOTES['08']);
}

module.exports = { createSlide };
