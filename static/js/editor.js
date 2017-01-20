/**
 * Created by abdulaziz on 11/19/14.
 */


;(function($){
  $.fn.markdown.messages['ar'] = {
    'Bold': "عريض",
    'Italic': "مائل",
    'Heading': "عنوان",
    'URL/Link': "رابط",
    'Image': "صورة",
    'List': "قائمة",
    'Preview': "معاينة",
    'Ordered List': "قائمة مرقمة",
    'Unordered List': "قائمة غير مرقمة",
    'strong text': "نص عريض",
    'emphasized text': "نص تأكيدي",
    'heading text': "العنوان",
    'enter link description here': "وصف الرابط",
    'Insert Hyperlink': "ادخل الرابط",
    'enter image description here': "اكتب وصف الصورة هنا",
    'Insert Image Hyperlink': "ادخل رابط الصورة هنا",
    'enter image title here': "عنوان الصورة",
    'list text here': "نص القائمة هنا",
    'quote here': 'اقتباس'
  };
}(jQuery))

var editor;
$("#id_markdown").markdown({
  language:'ar',
  additionalButtons: [
    [{
          name: "groupCustom",
          data: [{
            name: "cmdImgUpload",
            toggle: true, // this param only take effect if you load bootstrap.js
            title: "Upload Image",
            icon: "glyphicon glyphicon glyphicon glyphicon-cloud-upload",
            callback: function(e){
              var chunk, cursor,
                  selected = e.getSelection(), content = e.getContent()
              editor = e;
              $('.modal').modal('show')
            }
          }]
    }]
  ]
});