import { z } from 'zod';

/**
 * Wraps a ZodString schema to coerce null/undefined to an empty string
 * before validation, which is needed for PrimeVue form fields.
 */
export const stringFromNullish = (schema: z.ZodString) =>
  z.preprocess((val) => (val == null ? '' : val), schema);
