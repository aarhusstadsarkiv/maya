(function() {

    const results = [];
  
    // 1. Extract the main "intro" section with isMain = true
    const introSection = document.querySelector('.pure-g.full .intro');
    if (introSection) {
      // Heading from <h1>
      const headingEl = introSection.querySelector('h1.ng-binding');
      const heading = headingEl ? headingEl.innerText.trim() : '';
  
      // First paragraph from <p.manchet>
      const firstParagraphEl = introSection.querySelector('p.manchet');
      const firstParagraph = firstParagraphEl ? firstParagraphEl.innerText.trim() : '';
  
      // Additional paragraphs from within the <div ng-bind-html> section
      const extraParagraphContainer = introSection.querySelector('div[ng-bind-html]');
      const extraParagraphs = [];
      if (extraParagraphContainer) {
        const pElements = extraParagraphContainer.querySelectorAll('p');
        pElements.forEach(p => {
          const text = p.innerText.trim();
          if (text) extraParagraphs.push(text);
        });
      }
  
      // Combine paragraphs into a single array
      const paragraphs = [];
      if (firstParagraph) paragraphs.push(firstParagraph);
      paragraphs.push(...extraParagraphs);
  
      // Push our main object
      results.push({
        isMain: true,
        heading: heading,
        paragraphs: paragraphs,
        date: '',
        recordIds: []
      });
    }
  
    // 2. Extract the timeline slides with isMain = false
    const slides = document.querySelectorAll('.slide');
    slides.forEach(slide => {
      const metaContent = slide.querySelector('.slide-meta-content');
      if (!metaContent) return;
  
      // Date
      const dateEl = slide.querySelector('.slide-meta h1 span');
      const date = dateEl ? dateEl.innerText.trim() : '';
  
      // Heading
      const headingEl = metaContent.querySelector('p strong');
      const heading = headingEl ? headingEl.innerText.trim() : '';
  
      // Paragraphs
      const paragraphContainer = metaContent.querySelector('div[ng-bind-html]');
      const paragraphs = paragraphContainer
        ? Array.from(paragraphContainer.querySelectorAll('p'))
            .map(p => p.innerText.trim())
            .filter(Boolean)
        : [];
  
      // Record IDs
      const recordIdEls = slide.querySelectorAll('.pure-u-8-24.shadow .item-id.ng-binding');
      const recordIds = Array.from(recordIdEls).map(el => {
        return el.innerText.replace('Arkiv-id:', '').trim();
      });
  
      // Only add to results if we actually have relevant data
      if (date || heading || paragraphs.length > 0 || recordIds.length > 0) {
        results.push({
          isMain: false,
          date,
          heading,
          paragraphs,
          recordIds
        });
      }
    });
  
    // 3. Log out the collected data
    console.log(results);
  })();
  