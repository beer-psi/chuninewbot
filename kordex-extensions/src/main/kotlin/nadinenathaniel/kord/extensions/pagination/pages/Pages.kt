package nadinenathaniel.kord.extensions.pagination.pages

open class Pages(open var defaultGroup: String = "") {
    /** All groups of pages stored in this class. **/
    open val groups: LinkedHashMap<String, MutableList<Page>> = linkedMapOf()

    /** Add a page to the default group. **/
    open fun addPage(page: Page): Unit = addPage(defaultGroup, page)

    /** Add a page to a given group. **/
    open fun addPage(group: String, page: Page) {
        groups[group] = groups[group] ?: mutableListOf()

        groups[group]!!.add(page)
    }

    /** Retrieve the page at the given index, from the default group. **/
    open fun get(page: Int): Page = get(defaultGroup, page)

    /** Retrieve the page at the given index, from a given group. **/
    open fun get(group: String, page: Int): Page {
        if (groups[group] == null) {
            throw NoSuchElementException("No such group: $group")
        }

        val size = groups[group]!!.size

        if (page > size) {
            throw IndexOutOfBoundsException("Page out of range: $page ($size pages)")
        }

        return groups[group]!![page]
    }

    /** Check that this Pages object is valid, throwing if it isn't.. **/
    open fun validate() {
        if (groups.isEmpty()) {
            throw IllegalArgumentException(
                "Invalid pages supplied: At least one page is required"
            )
        }
    }
}
