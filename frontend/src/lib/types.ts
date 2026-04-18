export type ItemTyp = 'Box' | 'Regal' | 'Boden' | 'Schublade' | 'Sortierbox';

export interface Item {
  id: string;
  collectionId: string;
  box_nr: number;
  inhalt: string;
  typ: ItemTyp;
  bereich: string;
  image: string;
  created: string;
  updated: string;
}

export interface Credentials {
  pbUrl: string;
  pbToken: string;
  aioUsername: string;
  aioKey: string;
  anthropicKey: string;
}

export const TYP_COLOURS: Record<ItemTyp, string> = {
  Box:        'bg-blue-100 text-blue-800',
  Regal:      'bg-green-100 text-green-800',
  Boden:      'bg-yellow-100 text-yellow-800',
  Schublade:  'bg-purple-100 text-purple-800',
  Sortierbox: 'bg-orange-100 text-orange-800',
};

export const ALL_TYPEN: ItemTyp[] = ['Box', 'Regal', 'Boden', 'Schublade', 'Sortierbox'];
