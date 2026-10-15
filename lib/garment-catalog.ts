import catalog from '../security/garment-catalog.json' with {type:'json'};
export type Category='Top'|'Shirt'|'T-shirt'|'Sweater'|'Hoodie'|'Jacket'|'Pants'|'Jeans'|'Shorts'|'Skirt'|'Dress'|'Jumpsuit'|'Unsupported';
export type Audience='Women'|'Men'|'Unisex';
export type WearerProfile='Women'|'Men';
export const garmentCatalog=catalog as Array<{value:Category;group:string;native:'tops'|'bottoms'|'one-pieces'|null;maskIds:number[];prompt:string}>;
export const supportedCategories=garmentCatalog.filter(item=>item.native!==null).map(item=>item.value);
export function nativeCategory(category:string){const item=garmentCatalog.find(item=>item.value===category);if(!item?.native)throw new Error('This garment is not supported. Choose one top, lower-body garment or one-piece outfit.');return item.native}
export function compatibilityError(audience:Audience|undefined,profile:WearerProfile|undefined):string|null{
 if(!profile||!['Women','Men'].includes(profile))return 'Choose the wearer profile for this photo before starting. The app does not determine gender from a photo.';
 if(!audience||!['Women','Men','Unisex'].includes(audience))return 'Confirm the garment’s intended clothing range first.';
 if(audience!=='Unisex'&&audience!==profile)return `This garment is confirmed as ${audience}’s clothing, but the selected wearer profile is ${profile}. Review the garment range or choose a matching person photo/profile before trying it on.`;
 return null;
}
