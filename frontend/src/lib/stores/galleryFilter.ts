import { writable } from 'svelte/store';
import type { ItemTyp } from '$lib/types';

export const searchText = writable('');
export const filterTyp  = writable<ItemTyp | ''>('');
