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
  map?.startSlide({ slideNumber: 3, slideId: 'users', title: 'Who this is for' });
  title(slide, map, 'users.title', 'Who this is for', theme);

  const users = [
    { id: 'users.card.01', t: 'Pet-owning residents', d: 'Cannot judge plant toxicity themselves.' },
    { id: 'users.card.02', t: 'Landscape-architecture students', d: 'Need a defensible first draft, fast.' },
    { id: 'users.card.03', t: 'Junior planting designers', d: 'Need one design that satisfies every constraint at once.' },
  ];
  users.forEach((u, i) => {
    const y = 1.12 + i * 1.28;
    addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
      elementId: u.id + '.card', role: 'card',
      x: 0.55, y: y, w: 4.55, h: 1.05,
      options: { fill: { color: 'F6F7F6' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.06 },
      source: { file: 'slides/slide-03.js', method: 'addShape' },
    });
    addMappedShape(slide, map, pres.shapes.RECTANGLE, {
      elementId: u.id + '.stripe', role: 'decorative',
      x: 0.55, y: y, w: 0.09, h: 1.05,
      options: { fill: { color: theme.secondary }, line: { color: theme.secondary, width: 0 } },
      source: { file: 'slides/slide-03.js', method: 'addShape' },
    });
    addMappedText(slide, map, {
      elementId: u.id + '.title', role: 'heading', text: u.t,
      x: 0.85, y: y + 0.16, w: 4.1, h: 0.34,
      options: { fontSize: 15, bold: true, color: theme.primary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-03.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: u.id + '.desc', role: 'body', text: u.d,
      x: 0.85, y: y + 0.52, w: 4.1, h: 0.42,
      options: { fontSize: 11.5, color: '51605A', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-03.js', method: 'addText' },
    });
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'users.right.card', role: 'card',
    x: 5.35, y: 1.12, w: 4.1, h: 3.61,
    options: { fill: { color: theme.primary }, line: { color: theme.primary, width: 0 }, rectRadius: 0.06 },
    source: { file: 'slides/slide-03.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'users.right.heading', role: 'heading', text: 'Two constraints, one answer',
    x: 5.62, y: 1.4, w: 3.6, h: 0.4,
    options: { fontSize: 16, bold: true, color: GOLD, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-03.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'users.right.body', role: 'body',
    text: 'Horticultural viability\n   light + moisture must suit the site\n\nVeterinary safety\n   no species toxic to the household pets\n\nDesign space\n   balcony / courtyard / rooftop terrace',
    x: 5.62, y: 1.92, w: 3.6, h: 2.1,
    options: { fontSize: 12, color: 'E4EDE8', align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.12, fontFace: 'Arial' },
    source: { file: 'slides/slide-03.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'users.right.note', role: 'body',
    text: 'Both constraints must hold simultaneously, for every species in the scheme.',
    x: 5.62, y: 4.18, w: 3.6, h: 0.5,
    options: { fontSize: 11, italic: true, color: '9FC7BA', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-03.js', method: 'addText' },
  });
  pageNumber(slide, map, 3, theme);
  slide.addNotes(NOTES['03']);
}

module.exports = { createSlide };
