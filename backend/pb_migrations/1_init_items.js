/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
  const collection = new Collection({
    name: "items",
    type: "base",
    fields: [
      {
        name: "box_nr",
        type: "number",
        required: true,
        min: 1,
        noDecimal: true,
      },
      {
        name: "inhalt",
        type: "text",
        required: false,
      },
      {
        name: "typ",
        type: "select",
        required: true,
        maxSelect: 1,
        values: ["Box", "Regal", "Boden", "Schublade", "Sortierbox"],
      },
      {
        name: "bereich",
        type: "text",
        required: false,
      },
      {
        name: "image",
        type: "file",
        required: false,
        maxSelect: 1,
        maxSize: 10485760,
        mimeTypes: ["image/jpeg", "image/png", "image/webp"],
        thumbs: ["200x200", "800x600"],
      },
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_items_box_nr ON items (box_nr)",
    ],
  });

  app.save(collection);

}, (app) => {
  const collection = app.findCollectionByNameOrId("items");
  app.delete(collection);
});
