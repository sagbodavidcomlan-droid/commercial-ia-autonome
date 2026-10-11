function createTemplate() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet();
  var activeSheet = sheet.getActiveSheet();
  
  // Headers
  var headers = [
    'id', 'status', 'approval_status', 'template', 'zodiac_sign', 
    'music_mood', 'timezone', 'title', 'text_1', 'text_2', 'text_3', 
    'text_4', 'text_5', 'caption', 'hashtags', 'asset_keyword', 
    'schedule_datetime', 'music_source_type', 'music_source', 'music_query', 
    'music_mode', 'music_fade_in', 'music_fade_out', 'music_volume', 
    'music_normalize', 'beat_sync', 'animation', 'text_effect', 'transition', 
    'scrolling', 'scrolling_direction', 'watermark_text', 'watermark_position', 
    'logo_text', 'logo_position', 'outro_source', 'outro_duration'
  ];
  
  // Set headers
  activeSheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  // Set column widths
  activeSheet.setColumnWidths(1, 1, 60);  // id
  activeSheet.setColumnWidths(2, 1, 150); // status
  activeSheet.setColumnWidths(4, 1, 120); // template
  activeSheet.setColumnWidths(9, 5, 250); // text_1 to text_5
  
  // Format date column
  var dateRange = activeSheet.getRange('Q:Q');
  dateRange.setNumberFormat('yyyy-mm-dd hh:mm:ss');
  
  // Set data validation for dropdowns
  var statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['DRAFT', 'READY_RENDER', 'RENDERING', 'RENDERED', 
                         'WAITING_APPROVAL', 'APPROVED', 'REJECTED', 
                         'SENT_TO_NUELINK', 'ERROR'])
    .build();
  activeSheet.getRange('B:B').setDataValidation(statusRule);
  
  var templateRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['zodiac_dark', 'motivational', 'educational', 
                         'quote_simple', 'tips_daily'])
    .build();
  activeSheet.getRange('D:D').setDataValidation(templateRule);
  
  var zodiacRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['', 'aries', 'taurus', 'gemini', 'cancer', 'leo', 
                         'virgo', 'libra', 'scorpio', 'sagittarius', 
                         'capricorn', 'aquarius', 'pisces'])
    .build();
  activeSheet.getRange('E:E').setDataValidation(zodiacRule);
  
  var musicMoodRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['dark', 'cinematic', 'upbeat', 'motivational', 
                         'lofi', 'ambient', 'epic', 'happy', 'sad', 'beats'])
    .build();
  activeSheet.getRange('F:F').setDataValidation(musicMoodRule);
  
  // Set formula for auto-number id
  activeSheet.getRange('A2').setFormula('=ROW()-1');
  activeSheet.getRange('A2:A').copyTo(activeSheet.getRange('A2:A'), 
    SpreadsheetApp.CopyPasteType.PASTE_FORMULA, false);
  
  // Sample data row
  var sampleData = [
    ['', 'DRAFT', '', 'motivational', '', 'upbeat', 'Asia/Jakarta', 
     'Sample Video', 'This is a test video', 'n8n workflow is working', 
     '', '', '', 'Test caption #test', '#test', 'nature beautiful', 
     '2026-05-20 08:00:00', 'local', '', '', 'background', 2, 2, 0.7, true]
  ];
  
  activeSheet.getRange(2, 1, 1, sampleData[0].length).setValues(sampleData);
  
  SpreadsheetApp.getUi().alert('Template created successfully!');
}