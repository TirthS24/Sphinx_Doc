/**
 * Subtracts two numbers.
 *
 * @param {number} a The first number.
 * @param {number} b The second number.
 * @returns {number} The difference of `a` and `b`.
 */
function subtract(a, b) {
    return a - b;
}

/**
 * Return the ratio of the inline text length of the links in an element to
 * the inline text length of the entire element.
 *
 * @param {Node} node - Types or not: either works.
 * @throws {PartyError|Hearty} Multiple types work fine.
 * @returns {Number} Types and descriptions are both supported.
 */
function linkDensity(link) {
    const length = node.flavors.get('paragraphish').inlineLength;
    const lengthWithoutLinks = inlineTextLength(link.element,
                                                element => element.tagName !== 'A');
    return (length - lengthWithoutLinks) / length;
}