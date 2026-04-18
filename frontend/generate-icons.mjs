import sharp from 'sharp';

for (const size of [192, 512, 180]) {
  const padding = Math.round(size * 0.12);
  const iconSize = size - padding * 2;

  // Resize the sample, then composite white icon onto blue background.
  // sample.png is black-on-white → negate to white-on-black → use as overlay via 'screen' blend.
  const resized = await sharp('static/icons/sample.png')
    .resize(iconSize, iconSize, { fit: 'contain', background: '#ffffff' })
    .flatten({ background: '#ffffff' })
    .negate()         // now: white icon on black background
    .toBuffer();

  // Blue background
  const bg = await sharp({
    create: { width: size, height: size, channels: 3,
              background: { r: 30, g: 58, b: 95 } }
  }).png().toBuffer();

  // Composite: 'screen' blend makes black areas transparent, white areas show through
  await sharp(bg)
    .composite([{ input: resized, top: padding, left: padding, blend: 'screen' }])
    .png()
    .toFile(`static/icons/icon-${size}.png`);

  console.log(`✓ icon-${size}.png`);
}
